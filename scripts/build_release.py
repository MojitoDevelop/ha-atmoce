"""Build a numbered Atmoce release from the manifest and changelog."""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_release(output_dir: Path) -> dict[str, str]:
    """Produce a deterministic ZIP with integration files at its root."""
    component = ROOT / "custom_components/atmoce_mqtt"
    manifest = json.loads((component / "manifest.json").read_text())
    version = manifest["version"]
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise ValueError("Use a stable version in MAJOR.MINOR.PATCH format")
    changelog = (ROOT / "CHANGELOG.md").read_text()
    section = re.search(
        rf"^## {re.escape(version)}\s*\n(.*?)(?=^## |\Z)", changelog, re.M | re.S
    )
    if section is None or not section[1].strip():
        raise ValueError(f"Missing release notes for {version} in CHANGELOG.md")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / "atmoce_mqtt.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(component.rglob("*")):
            if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            if path.is_symlink():
                raise ValueError(f"Release contains a symbolic link: {path}")
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(component).as_posix())
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, path.read_bytes())
    notes = output_dir / "release-notes.md"
    notes.write_text(section[1].strip() + "\n")
    checksum = output_dir / "SHA256SUMS"
    checksum.write_text(
        f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n"
    )
    return {
        "version": version,
        "tag": f"v{version}",
        "archive": str(archive),
        "notes": str(notes),
        "checksum": str(checksum),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = build_release(args.output_dir)
    if args.github_output:
        with args.github_output.open("a") as output:
            for key, value in result.items():
                output.write(f"{key}={value}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
