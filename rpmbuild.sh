#!/bin/bash
# Builds RPM for current git commit.
set -exuo pipefail

if ! git diff-index --quiet HEAD --; then
    echo "Commit your changes first."
    exit 1
fi

tmpdir=$(mktemp --directory)
trap 'rm -rf $tmpdir' EXIT

make -f .copr/Makefile outdir=$tmpdir dist_dir=$tmpdir srpm

mock -r epel-7-x86_64 \
    --rebuild $tmpdir/*.src.rpm \
    --resultdir=rpmbuild

echo "Results saved in rpmbuild/."
