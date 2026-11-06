# Fetch CC0 photo-scan PBR sets (Poly Haven, ambientCG) and pack each into the three WebP maps
# the template's materials.js loads: <name>_c (colour, sRGB), <name>_n (normal, OpenGL),
# <name>_r (R = ambient occlusion, G = roughness). 1K source, resized per set.
#   python3 textures.py <download-dir> <out-dir> [name ...]     (no names = every set in MANIFEST)
#   python3 textures.py --measure <out-dir> [name ...]           mean linear albedo per set
#   python3 textures.py --downscale 512 <out-dir> [<dst-dir>]    the phone tier (default <out-dir>/512)
# Adding a finish: add a line to MANIFEST, run this, then measure its mean linear albedo with
# --measure and add it to SET_AVG in src/styles.js so roles can name finishes by albedo.
import io, json, os, shutil, sys, urllib.request, zipfile, concurrent.futures as cf
from PIL import Image, ImageOps

# name: (source, id, size, grayscale[, contrast]). Grayscale sets are neutralised and tinted by the
# material colour instead, which keeps a finish's hue under the designer's control and hides the
# scan's cast. contrast (default 1) compresses the colour map's linear contrast about its mean,
# out = mean + (lin - mean) * k: a scan divided up to a near-white albedo (styles.js SET_AVG) would
# otherwise push half its texels past 1 and clip; the mean itself is unchanged, so SET_AVG holds.
MANIFEST = {
  'plaster': ('ph', 'painted_plaster_wall', 1024, False), 'stone': ('ph', 'rectangular_facade_tiles', 1024, False),
  'walnut': ('ph', 'walnut_veneer', 1024, False), 'oak': ('ph', 'white_oak_veneer', 1024, False),
  'woodfloor': ('ph', 'wood_floor', 1024, False), 'patio': ('ph', 'large_floor_tiles_02', 1024, False),
  'pavers': ('ph', 'concrete_pavers_02', 1024, True), 'sidewalk': ('ph', 'square_concrete_pavers', 1024, True),
  'asphalt': ('ph', 'clean_asphalt', 1024, False), 'sand': ('ph', 'aerial_sand', 1024, True),
  'gravel': ('ph', 'gravel_floor_02', 512, False), 'bark': ('ph', 'palm_tree_bark', 512, False),
  'velvet': ('ph', 'velour_velvet', 512, True), 'rug': ('acg', 'Carpet016', 512, False),
  'boucle': ('acg', 'Fabric045', 512, True, 0.6), 'linen': ('acg', 'Fabric066', 512, True, 0.4),
  'grass': ('acg', 'Grass001', 1024, False), 'marble': ('acg', 'Marble012', 1024, False),
  'travertine': ('acg', 'Travertine009', 1024, False),
  # style sets (loaded on first use of a style)
  'ash': ('ph', 'ash_veneer', 1024, False), 'herringbone': ('ph', 'herringbone_parquet', 1024, False),
  'smokedwalnut': ('ph', 'smoked_walnut_veneer', 1024, False), 'terracotta': ('ph', 'terracotta_floor_tiles', 1024, False),
  'clayplaster': ('ph', 'clay_plaster', 1024, True), 'limewash': ('acg', 'Plaster003', 1024, True),
  'microcement': ('acg', 'Concrete034', 1024, True), 'rattan': ('acg', 'Wicker004', 512, False),
  'papercord': ('acg', 'Wicker006', 512, True), 'nero': ('acg', 'Marble016', 1024, False),
}

def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'texture-fetch/1.0'}), timeout=120) as r:
        return r.read()

# sRGB <-> linear lookup tables, shared by the contrast step and the measurement
LIN = [((v / 255) / 12.92 if v / 255 <= 0.04045 else (((v / 255) + 0.055) / 1.055) ** 2.4) for v in range(256)]
def srgb(l):
    l = min(1.0, max(0.0, l))
    return int(round((l * 12.92 if l <= 0.0031308 else 1.055 * l ** (1 / 2.4) - 0.055) * 255))

def compress_contrast(col, k):
    """Pull each channel's linear values towards its mean by k, through one LUT per channel."""
    hist, bands = col.histogram(), []
    for c in range(3):
        h = hist[c * 256:(c + 1) * 256]
        mean = sum(LIN[v] * h[v] for v in range(256)) / max(1, sum(h))
        bands.append(col.getchannel(c).point([srgb(mean + (LIN[v] - mean) * k) for v in range(256)]))
    return Image.merge('RGB', bands)

def fetch(dl, name):
    src, i, size, gray = MANIFEST[name][:4]
    d = os.path.join(dl, name); os.makedirs(d, exist_ok=True)
    if src == 'ph':
        f = json.loads(get('https://api.polyhaven.com/files/' + i))
        for k in ['Diffuse', 'nor_gl', 'Rough', 'AO']:
            if k in f: open(os.path.join(d, k + '.jpg'), 'wb').write(get(f[k]['1k']['jpg']['url']))
    else:
        z = zipfile.ZipFile(io.BytesIO(get(f'https://ambientcg.com/get?file={i}_1K-JPG.zip')))
        for n in z.namelist():
            for k, tag in [('_Color', 'Diffuse'), ('_NormalGL', 'nor_gl'), ('_Roughness', 'Rough'), ('_AmbientOcclusion', 'AO')]:
                if n.endswith('.jpg') and k in n: open(os.path.join(d, tag + '.jpg'), 'wb').write(z.read(n))
    return d

def pack(d, out, name):
    _, _, size, gray = MANIFEST[name][:4]
    contrast = MANIFEST[name][4] if len(MANIFEST[name]) > 4 else 1.0
    o = lambda k: Image.open(os.path.join(d, k + '.jpg'))
    col = o('Diffuse').convert('RGB').resize((size, size), Image.LANCZOS)
    if gray:  # low-contrast neutral: the material colour supplies the hue, the scan supplies the grain
        g = ImageOps.autocontrast(col.convert('L'), cutoff=1); col = g.point(lambda v: int(70 + v * 0.72)).convert('RGB')
    if contrast != 1.0:
        col = compress_contrast(col, contrast)
    nor = o('nor_gl').convert('RGB').resize((size, size), Image.LANCZOS)
    rough = o('Rough').convert('L').resize((size, size), Image.LANCZOS)
    ao = o('AO').convert('L').resize((size, size), Image.LANCZOS) if os.path.exists(os.path.join(d, 'AO.jpg')) else Image.new('L', (size, size), 255)
    arm = Image.merge('RGB', (ao, rough, Image.new('L', (size, size), 0)))
    tot = 0
    for suf, im, q in (('c', col, 82), ('n', nor, 90), ('r', arm, 80)):
        p = os.path.join(out, f'{name}_{suf}.webp'); im.save(p, 'WEBP', quality=q, method=6); tot += os.path.getsize(p)
    return tot

def measure(out, names):
    """Mean linear albedo of each packed colour map, for SET_AVG in src/styles.js and the GI bake."""
    # linearise every texel first, then average: averaging gamma-encoded values (or a resized
    # image) understates bright, contrasty scans by up to 20 %
    res = {}
    for name in names:
        im = Image.open(os.path.join(out, f'{name}_c.webp')).convert('RGB')
        hist = im.histogram()
        res[name] = [round(sum(LIN[v] * hist[c * 256 + v] for v in range(256)) / (im.width * im.height), 3) for c in range(3)]
    return res

def downscale(size, src, dst):
    """The phone tier: every packed map Lanczos-resized to size px (files already that small are
    copied), WebP quality 82, method 6. The page reads it from assets/tex/<size>/ on the low tier."""
    os.makedirs(dst, exist_ok=True)
    tot = 0
    for f in sorted(os.listdir(src)):
        if not f.endswith('.webp'): continue
        p, q = os.path.join(src, f), os.path.join(dst, f)
        im = Image.open(p)
        if max(im.size) <= size: shutil.copyfile(p, q)
        else: im.resize((size, size), Image.LANCZOS).save(q, 'WEBP', quality=82, method=6)
        tot += os.path.getsize(q)
    print(f'{dst}: {tot / 1e6:.2f} MB')

if __name__ == '__main__':
    if sys.argv[1] == '--measure':
        print(json.dumps(measure(sys.argv[2], sys.argv[3:] or list(MANIFEST)))); sys.exit()
    if sys.argv[1] == '--downscale':
        size, src = int(sys.argv[2]), sys.argv[3]
        downscale(size, src, sys.argv[4] if len(sys.argv) > 4 else os.path.join(src, str(size))); sys.exit()
    dl, out = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or list(MANIFEST)
    os.makedirs(out, exist_ok=True)
    with cf.ThreadPoolExecutor(6) as ex:
        for name, size in zip(names, ex.map(lambda n: pack(fetch(dl, n), out, n), names)):
            print(f'{name}: {size / 1e3:.0f} kB')
    print(json.dumps(measure(out, names)))
