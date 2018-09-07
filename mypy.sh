#!/bin/sh
# Add in `--disallow-untyped-calls` once aiohttp is fully typed.
python3 -m mypy --strict-optional --ignore-missing-imports --warn-unused-ignores --warn-redundant-casts --disallow-untyped-defs ni/*.py
