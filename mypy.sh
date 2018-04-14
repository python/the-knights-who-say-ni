#!/bin/sh
python3 -m mypy --strict-optional --ignore-missing-imports --warn-unused-ignores --warn-redundant-casts --disallow-untyped-defs --disallow-untyped-calls ni/*.py
