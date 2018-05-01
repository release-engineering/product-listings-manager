#!/bin/bash

set -euv

docker run \
    --rm \
    -e TOXENV="${TOXENV}" \
    -t \
    product-listings-manager \
