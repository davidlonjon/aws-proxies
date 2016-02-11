#!/usr/bin/env bash
#
gitchangelog > CHANGELOG.md
pandoc --from=markdown --to=rst --output=CHANGELOG.rst CHANGELOG.md