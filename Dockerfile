FROM registry.access.redhat.com/ubi8/ubi:8.7 as builder

# hadolint ignore=DL3033,DL4006,SC2039,SC3040
RUN set -exo pipefail \
    && mkdir -p /mnt/rootfs \
    # install builder dependencies
    && yum install -y \
        --setopt install_weak_deps=false \
        --nodocs \
        gcc \
        krb5-devel \
        python39 \
        python39-devel \
    # install runtime dependencies
    && yum install -y \
        --installroot=/mnt/rootfs \
        --releasever=8 \
        --setopt install_weak_deps=false \
        --nodocs \
        python39 \
    && yum --installroot=/mnt/rootfs clean all \
    && rm -rf /mnt/rootfs/var/cache/* /mnt/rootfs/var/log/dnf* /mnt/rootfs/var/log/yum.* \
    # https://python-poetry.org/docs/master/#installing-with-the-official-installer
    && curl -sSL https://install.python-poetry.org | python3 - \
    && python3 -m venv /venv

ENV \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY . .
# hadolint ignore=SC1091
RUN set -ex \
    && export PATH=/root/.local/bin:$PATH \
    && . /venv/bin/activate \
    && pip install --no-cache-dir -r requirements.txt \
    && poetry build --format=wheel \
    && version=$(poetry version --short) \
    && pip install --no-cache-dir dist/product_listings_manager-"$version"-py3*.whl \
    && deactivate \
    && mv /venv /mnt/rootfs \
    && mkdir -p /mnt/rootfs/src/docker \
    && cp -v docker/docker-entrypoint.sh /mnt/rootfs/src/docker

# --- Final image
FROM scratch
ARG GITHUB_SHA
LABEL \
    name="product-listings-manager" \
    vendor="product-listings-manager developers" \
    summary="Product Listings Manager application" \
    description="HTTP API for finding product listings and interacting with data in composedb." \
    maintainer="Red Hat, Inc." \
    license="MIT" \
    url="https://github.com/release-engineering/product-listings-manager" \
    vcs-type="git" \
    vcs-ref=$GITHUB_SHA \
    io.k8s.display-name="Product Listings Manager"

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=8

COPY --from=builder /mnt/rootfs/ /
COPY --from=builder /etc/yum.repos.d/ubi.repo /etc/yum.repos.d/ubi.repo
WORKDIR /src

USER 1001
EXPOSE 8080
ENTRYPOINT ["/src/docker/docker-entrypoint.sh"]
CMD [ \
    "gunicorn", \
    "--bind=0.0.0.0:5000", \
    "--access-logfile=-", \
    "--enable-stdio-inheritance", \
    "product_listings_manager.wsgi" \
    ]
