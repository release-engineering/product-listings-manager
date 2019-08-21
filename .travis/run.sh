#!/bin/bash

set -euv

docker run \
    --rm \
    -e TOXENV="${TOXENV}" \
    -t \
    -v $(pwd):/build \
    product-listings-manager \
