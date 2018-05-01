#!/bin/bash

set -euv

if [ "${CONTAINER_IMAGE}" = "" ]; then
    echo "Container image not defined." 1>&2
    exit 1
fi

DOCKER_FILE=".travis/Dockerfile.${CONTAINER_IMAGE}"

if [ ! -f $DOCKER_FILE ]; then
    echo "$DOCKER_FILE does not exist." 1>&2
    exit 1
fi

export DOCKER_FILE

docker build \
    --rm \
    -t product-listings-manager \
    -f $DOCKER_FILE \
    .
