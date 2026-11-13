# Atmoce artwork

The ATMOCE emblem and wordmark come from the manufacturer's website:

- Website: https://www.atmoce.com/en
- SVG sprite: https://www.atmoce.com/_nuxt/en/entry.DGYXNWLJ.js
- Symbols: `icon-logo` and `icon-logoText`
- Retrieved: 2026-11-13

The original vector paths are kept in `assets/atmoce/` in the repository.
PNG exports preserve the artwork and use its `currentColor` in black for light
backgrounds and white for dark backgrounds. ATMOCE artwork belongs to Atmoce;
it is not covered by this project's MIT license.

To reproduce the exports from the repository root:

```bash
uv run --with resvg-py==0.5.0 python scripts/render_brand.py
```
