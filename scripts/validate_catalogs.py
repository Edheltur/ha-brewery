"""Validate brewery schemas, examples, and bundled catalogs."""

import json
import math
import os
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path(os.environ.get("BREWERY_PACKAGE_DIR", ROOT / "dist" / "brewery")).resolve()
SCHEMAS = PACKAGE / "schemas"
DATA = PACKAGE / "data"
CATALOG_SCHEMAS = {
    "bjcp-2021.json": "bjcp.json",
    "water_profiles.json": "water_profiles.json",
    "salts.json": "salts.json",
}


def unique_object(pairs):
    """Reject duplicate JSON object keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def finite_number(token):
    """Reject non-finite JSON constants and overflowing exponents."""
    value = float(token)
    if not math.isfinite(value):
        raise ValueError(f"non-finite number {token}")
    return value


def read_json(path):
    """Read a strict JSON document with filename context for errors."""
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_float=finite_number,
            parse_constant=finite_number,
        )
    except (OSError, ValueError) as error:
        raise ValueError(f"{path.relative_to(PACKAGE)}: {error}") from error


def check_references(node, resolver, location):
    """Resolve schema references against the local registry."""
    if isinstance(node, dict):
        if "$id" in node:
            resolver = resolver.in_subresource(Resource.from_contents(node))
        if "$ref" in node:
            reference = node["$ref"]
            try:
                resolver.lookup(reference)
            except Unresolvable as error:
                raise ValueError(f"{location}.$ref: unresolved reference {reference!r}") from error
        for key, value in node.items():
            check_references(value, resolver, f"{location}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            check_references(value, resolver, f"{location}[{index}]")


def load_validators():
    """Load Draft 2020-12 schemas without a network retrieval callback."""
    paths = sorted(SCHEMAS.glob("*.json"))
    paths.extend(sorted((SCHEMAS / "vendor" / "beerjson").glob("*.json")))
    schemas = {path: read_json(path) for path in paths}
    registry = Registry()
    ids = set()
    for path, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            location = f"{path.relative_to(PACKAGE)}: {error.json_path}"
            raise ValueError(f"{location}: {error.message}") from error
        schema_id = schema.get("$id") if isinstance(schema, dict) else None
        if not schema_id:
            raise ValueError(f"{path.relative_to(PACKAGE)}: missing schema ID")
        if schema_id in ids:
            raise ValueError(f"{path.relative_to(PACKAGE)}: duplicate schema ID {schema_id}")
        ids.add(schema_id)
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    validators = {}
    for path, schema in schemas.items():
        check_references(schema, registry.resolver(), str(path.relative_to(PACKAGE)))
        validators[path.relative_to(SCHEMAS).as_posix()] = Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
    for schema_name in CATALOG_SCHEMAS.values():
        if schema_name not in validators:
            raise ValueError(f"{SCHEMAS.relative_to(PACKAGE) / schema_name}: missing catalog schema")
    return validators


def check_catalog_links(catalogs):
    """Check catalog rules spanning multiple entries or documents."""
    bjcp = catalogs["bjcp-2021.json"]
    profiles = catalogs["water_profiles.json"]
    salts = catalogs["salts.json"]
    styles = set()
    codes = set()
    for category_index, category in enumerate(bjcp["categories"]):
        for style_index, style in enumerate(category["styles"]):
            location = f"bjcp-2021.json: categories[{category_index}].styles[{style_index}]"
            identity = style["code"], style["name"]
            if identity in styles:
                yield f"{location}: duplicate BJCP style {identity!r}"
            styles.add(identity)
            codes.add(style["code"])
            for metric, entry in style["ranges"].items():
                intervals = {"": entry} if "min" in entry else entry
                for variant, bounds in intervals.items():
                    suffix = f".{variant}" if variant else ""
                    if bounds["min"] > bounds["max"]:
                        yield f"{location}.ranges.{metric}{suffix}: min exceeds max"

    if profiles["bjcp_edition"] != bjcp["edition"]:
        yield (
            "water_profiles.json: bjcp_edition "
            f"{profiles['bjcp_edition']} does not match catalog edition {bjcp['edition']}"
        )
    for index, profile in enumerate(profiles["profiles"]):
        for code_index, code in enumerate(profile["bjcp_styles"]):
            if code not in codes:
                yield (
                    f"water_profiles.json: profiles[{index}].bjcp_styles[{code_index}]: "
                    f"unknown code {code!r} in BJCP {bjcp['edition']}"
                )

    for filename, key, entries in (
        ("water_profiles.json", "profiles", profiles["profiles"]),
        ("salts.json", "salts", salts["salts"]),
    ):
        names = set()
        for index, entry in enumerate(entries):
            name = entry["name"]
            if name in names:
                yield f"{filename}: {key}[{index}].name: duplicate name {name!r}"
            names.add(name)


def main():
    """Return a nonzero exit status if any validation fails."""
    try:
        validators = load_validators()
        catalogs = {filename: read_json(DATA / filename) for filename in CATALOG_SCHEMAS}
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    errors = [
        f"{filename}: {error.json_path}: {error.message}"
        for filename, schema in CATALOG_SCHEMAS.items()
        for error in validators[schema].iter_errors(catalogs[filename])
    ]
    if not errors:
        errors.extend(check_catalog_links(catalogs))
    errors.extend(
        f"{filename}: examples[{index}] {error.json_path}: {error.message}"
        for filename, validator in validators.items()
        for index, example in enumerate(validator.schema.get("examples", []))
        for error in validator.iter_errors(example)
    )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"Validated {len(catalogs)} catalogs, schema examples, and local schema references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
