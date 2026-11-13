"""Export the approved Atmoce icon and wordmark to Home Assistant brand images."""

import base64
import xml.etree.ElementTree as ET
from pathlib import Path

import resvg_py

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components/atmoce_mqtt/brand"


def main() -> None:
    """Preserve the published square icon and use plain wordmarks for wide logos."""
    icon = base64.b64encode((ROOT / "assets/atmoce/icon.jpg").read_bytes()).decode()
    for theme, color in (("", "#000000"), ("dark_", "#ffffff")):
        for scale, suffix in ((1, ""), (2, "@2x")):
            size = 256 * scale
            # An SVG wrapper only scales/converts the original JPEG to PNG.
            icon_svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
                f'height="{size}" viewBox="0 0 400 400">'
                f'<image width="400" height="400" href="data:image/jpeg;base64,{icon}"/>'
                "</svg>"
            )
            icon_output = BRAND / f"{theme}icon{suffix}.png"
            icon_output.write_bytes(resvg_py.svg_to_bytes(svg_string=icon_svg))
            print(icon_output.relative_to(ROOT))

            svg = ET.fromstring((ROOT / "assets/atmoce/wordmark.svg").read_text())
            svg.set("color", color)
            _, _, width, height = map(float, svg.attrib["viewBox"].split())
            svg.set("width", str(round(width / height * 128 * scale)))
            svg.set("height", str(128 * scale))
            logo_output = BRAND / f"{theme}logo{suffix}.png"
            logo_output.write_bytes(
                resvg_py.svg_to_bytes(svg_string=ET.tostring(svg, encoding="unicode"))
            )
            print(logo_output.relative_to(ROOT))


if __name__ == "__main__":
    main()
