#!/bin/sh
mypy --python-version 3.6 --fast-parser --strict-optional --silent-imports --warn-redundant-casts --disallow-untyped-defs ni/*.py
