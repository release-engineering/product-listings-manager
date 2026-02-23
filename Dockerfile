FROM quay.io/fedora/python-313:20260218@sha256:654df0c971e86e9ecb781e55a7d7860b7e07bc66c8f60d1ce2c28ef09d1556c3 AS builder

# builder should use root to install/create all files
USER root

# hadolint ignore=DL3033,DL3041,DL4006,SC2039,SC3040
RUN set -exo pipefail \
    && mkdir -p /mnt/rootfs \
    # install runtime dependencies
    && dnf install -y \
        --installroot=/mnt/rootfs \
        --use-host-config \
        --setopt install_weak_deps=false \
        --nodocs \
        --disablerepo=* \
        --enablerepo=fedora,updates \
        krb5-libs \
        openldap \
        python3 \
    && dnf --installroot=/mnt/rootfs clean all \
    # Install uv
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && python3 -m venv /venv

ENV \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Copy only specific files to avoid accidentally including any generated files
# or secrets.
COPY product_listings_manager ./product_listings_manager
COPY \
    pyproject.toml \
    uv.lock \
    README.rst \
    docker/docker-entrypoint.sh \
    docker/logging.ini \
    ./

ARG SHORT_COMMIT
ARG COMMIT_TIMESTAMP

# hadolint ignore=SC1091
RUN set -ex \
    && export PATH=/root/.cargo/bin:"$PATH" \
    && . /venv/bin/activate \
    && uv version "1.1.2.dev$COMMIT_TIMESTAMP+git.$SHORT_COMMIT" \
    && uv build --wheel \
    && version=$(uv version --short) \
    && pip install --no-cache-dir dist/product_listings_manager-"$version"-py3*.whl \
    && deactivate \
    && mv /venv /mnt/rootfs \
    && mkdir -p /mnt/rootfs/src/docker \
    && cp -v docker-entrypoint.sh /mnt/rootfs/src/docker \
    && cp -v logging.ini /mnt/rootfs/src/docker

# This is just to satisfy linters
USER 1001

# --- Final image
FROM scratch
LABEL \
    name="product-listings-manager" \
    vendor="product-listings-manager developers" \
    summary="Product Listings Manager application" \
    description="HTTP API for finding product listings and interacting with data in composedb." \
    maintainer="Red Hat, Inc." \
    license="MIT" \
    url="https://github.com/release-engineering/product-listings-manager" \
    io.k8s.display-name="Product Listings Manager"

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=8

COPY --from=builder /mnt/rootfs/ /
COPY --from=builder \
    /etc/yum.repos.d/fedora.repo \
    /etc/yum.repos.d/fedora-updates.repo \
    /etc/yum.repos.d/
WORKDIR /src

USER 1001
EXPOSE 8080

# Validate virtual environment
RUN /src/docker/docker-entrypoint.sh gunicorn --version \
    && /src/docker/docker-entrypoint.sh python -c \
      'from product_listings_manager import __version__; print(__version__)'

ENTRYPOINT ["/src/docker/docker-entrypoint.sh"]
CMD [ \
    "gunicorn", \
    "--bind=0.0.0.0:5000", \
    "--access-logfile=-", \
    "--enable-stdio-inheritance", \
    "--worker-class=uvicorn.workers.UvicornWorker", \
    "--log-config=/src/docker/logging.ini", \
    "product_listings_manager.wsgi" \
    ]
