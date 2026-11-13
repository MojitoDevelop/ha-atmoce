# Atmoce artwork

## Square icon

White ATMOCE wordmark on a coral gradient, published by ATMOCE with its press
release dated 2025-10-30:

- Press release: https://en.prnasia.com/releases/apac/atmoce-enters-australia-with-advanced-solar-power-generator-solutions-509265.shtml
- Original image: https://mma.prnasia.com/media2/2808867/ATMOCE_Logo.jpg
- Repository source: `assets/atmoce/icon.jpg` (the unmodified downloaded image)
- Retrieved: 2026-11-13

Both themes use this same published image. PNG exports only resize and convert
it to the required 256 × 256 and 512 × 512 icon formats.

## Wide wordmark

The plain ATMOCE wordmark comes from the manufacturer's website:

- Website: https://www.atmoce.com/en
- SVG sprite: https://www.atmoce.com/_nuxt/en/entry.DGYXNWLJ.js
- Symbol: `icon-logoText`
- Repository source: `assets/atmoce/wordmark.svg`

The vector paths are preserved, using black for light backgrounds and white for
dark backgrounds. The old emblem is not used.

ATMOCE artwork belongs to Atmoce and is not covered by this project's MIT license.

To reproduce the exports from the repository root:

```bash
uv run --with resvg-py==0.5.0 python scripts/render_brand.py
```
