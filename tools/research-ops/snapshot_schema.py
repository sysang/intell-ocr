"""Validate managed snapshots against the bundled, offline JSON Schema."""
import json
from functools import cache
from itertools import islice
from pathlib import Path

SCHEMA = Path(__file__).with_name('project-state.schema.json')


@cache
def validator():
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
        from referencing import Registry
    except ImportError as exc:
        raise ValueError('managed schema validator unavailable; install tools/research-ops/requirements.txt into the bound Python') from exc
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f'invalid bundled JSON Schema: {exc.message}') from exc
    # All schema references must resolve locally; the registry has no remote retriever.
    return Draft202012Validator(schema, registry=Registry())


def violations(state):
    try:
        compiled = validator()
    except (OSError, ValueError) as exc:
        return [f'managed schema unavailable: {exc}']

    from referencing.exceptions import Unresolvable
    try:
        errors = compiled.iter_errors(state)
        return [f'managed schema {error.json_path}: {error.message[:240]}' for error in islice(errors, 12)]
    except Unresolvable as exc:
        return [f'managed schema has an unresolved local reference: {exc}']
