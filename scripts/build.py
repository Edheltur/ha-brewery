"""Build the HACS release ZIP with local copies of the npm package's schemas."""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "brewery"
BEERJSON = ROOT / "node_modules" / "@beerjson" / "beerjson"
DIST = ROOT / "dist"


def main():
    upstream_schemas = BEERJSON / "json"
    if not (upstream_schemas / "beer.json").is_file():
        raise SystemExit("Install build dependencies with npm ci before building.")

    DIST.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=DIST) as temporary:
        archive = Path(temporary) / "brewery.zip"
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            for path in sorted(COMPONENT.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                    bundle.write(path, path.relative_to(COMPONENT))
            for path in [*sorted(upstream_schemas.glob("*.json")), BEERJSON / "LICENSE"]:
                bundle.write(path, f"schemas/vendor/beerjson/{path.name}")
        archive.replace(DIST / archive.name)


if __name__ == "__main__":
    main()
