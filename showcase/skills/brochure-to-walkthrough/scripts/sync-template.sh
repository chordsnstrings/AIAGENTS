#!/usr/bin/env bash
# Snapshot the reference project into this skill's template (assets/template): sources, bundle,
# textures and scripts, without modules, captures or scratch files.
# usage: scripts/sync-template.sh <path-to-reference-project>
set -eu
SRC=${1:?reference project path}; DST="$(cd "$(dirname "$0")/.." && pwd)/assets/template"
rm -rf "$DST"; mkdir -p "$DST"
( cd "$SRC" && tar --exclude=node_modules --exclude=out --exclude=shots --exclude=HANDOFF.md --exclude='*.log' \
    --exclude=rv --exclude=rvm --exclude=nt --exclude=sty --exclude=gi --exclude=dec --exclude='cap*' -cf - . ) | ( cd "$DST" && tar -xf - )
( cd "$SRC" && git rev-parse --short HEAD 2>/dev/null || echo unknown ) > "$DST/TEMPLATE_VERSION"
du -sh "$DST"; cat "$DST/TEMPLATE_VERSION"
