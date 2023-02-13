#!/bin/bash
set -eu

if [[ $GITHUB_REF =~ ^ref/tags/v ]]; then
    echo "${GITHUB_REF#refs/tags/v}"
else
    last_version=$(poetry version --short)
    echo "$last_version+git.${GITHUB_SHA:0:7}"
fi
