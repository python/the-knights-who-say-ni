#!/bin/sh
mypy --python-version 3.6 --fast-parser --strict-optional --ignore-missing-imports --warn-unused-ignores --warn-redundant-casts --disallow-untyped-defs --disallow-untyped-calls ni/*.py
