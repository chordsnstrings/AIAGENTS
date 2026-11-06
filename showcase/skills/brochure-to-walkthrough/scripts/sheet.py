# Contact sheet of capture stills: python3 sheet.py <dir-of-p*.png> <out.jpg> <columns> <thumb-width>
import sys, glob, os
from PIL import Image, ImageDraw
src, out, cols, tw = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
files = sorted(glob.glob(os.path.join(src, 'p*.png')), key=lambda f: float(os.path.basename(f)[1:-4]))
ims = [Image.open(f).convert('RGB') for f in files]
th = int(tw * ims[0].height / ims[0].width)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * th), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * tw, (i // cols) * th
    sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
    d.rectangle([x, y, x + 58, y + 14], fill=(0, 0, 0))
    d.text((x + 3, y + 2), os.path.basename(f)[:-4], fill=(255, 255, 0))
sheet.save(out, quality=88)
print(out, sheet.size)
