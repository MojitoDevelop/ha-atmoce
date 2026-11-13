"""Export Atmoce's vector artwork to Home Assistant's brand image sizes."""

import xml.etree.ElementTree as ET
from pathlib import Path

import resvg_py

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components/atmoce_mqtt/brand"


def main() -> None:
    """Use the original SVG paths and the site's black/white currentColor variants."""
    for theme, color in (("", "#000000"), ("dark_", "#ffffff")):
        for scale, suffix in ((1, ""), (2, "@2x")):
            for kind, source in (("icon", "logo"), ("logo", "wordmark")):
                svg = ET.fromstring((ROOT / f"assets/atmoce/{source}.svg").read_text())
                svg.set("color", color)
                if kind == "icon":
                    svg.set("width", str(256 * scale))
                    svg.set("height", str(256 * scale))
                    svg.set("preserveAspectRatio", "xMidYMid meet")
                else:
                    _, _, width, height = map(float, svg.attrib["viewBox"].split())
                    svg.set("width", str(round(width / height * 128 * scale)))
                    svg.set("height", str(128 * scale))
                output = BRAND / f"{theme}{kind}{suffix}.png"
                output.write_bytes(
                    resvg_py.svg_to_bytes(
                        svg_string=ET.tostring(svg, encoding="unicode")
                    )
                )
                print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
