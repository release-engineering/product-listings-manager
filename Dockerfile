FROM centos:8
LABEL \
    name="product-listings-manager" \
    vendor="product-listings-manager developers" \
    license="MIT" \
    build-date=""

RUN yum -y update \
    && yum -y install \
        gcc \
        git \
        krb5-devel \
        postgresql-devel \
        python36 \
        python36-devel \
        redhat-rpm-config \
        rpm-devel \
    && yum -y clean all \
    && rm -rf /var/cache/dnf \
    && rm -rf /tmp/*

WORKDIR /var/www/product-listings-manager

# Restore working tree from current git commit in container.
COPY .git .git
RUN git reset --hard HEAD \
    && git checkout HEAD

RUN pip3 install --no-cache-dir \
        -r requirements.txt \
        gunicorn \
        futures

ARG cacert_url
RUN if [ -n "$cacert_url" ]; then \
        cd /etc/pki/ca-trust/source/anchors \
        && curl -O --insecure $cacert_url \
        && update-ca-trust extract; \
    fi

USER 1001
EXPOSE 5000

ENTRYPOINT [ \
    "gunicorn", \
    "--bind=0.0.0.0:5000", \
    "--access-logfile=-", \
    "--enable-stdio-inheritance", \
    "product_listings_manager.wsgi" \
    ]
