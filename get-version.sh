#!/bin/bash
set -eu

if [[ $GITHUB_REF =~ ^ref/tags/v ]]; then
    echo "${GITHUB_REF#refs/tags/v}"
else
    last_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    echo "$last_version+git.${GITHUB_SHA:0:7}"
fi
