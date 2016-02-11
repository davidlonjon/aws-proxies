#!/usr/bin/env bash
# taken from https://github.com/donnemartin/saws/blob/master/scripts/create_readme_rst.sh

pandoc --from=markdown --to=rst --output=README.rst README.md