FROM centos:7
LABEL \
    name="product-listings-manager" \
    vendor="product-listings-manager developers" \
    license="MIT" \
    build-date=""

RUN yum install -y epel-release \
    && yum -y update \
    && yum -y install \
        git \
        python-gunicorn \
        python-flask \
        python2-flask-restful \
        python2-koji \
        PyGreSQL

WORKDIR /var/www/product-listings-manager

# Restore working tree from current git commit in container.
COPY .git .git
RUN git reset --hard HEAD \
    && git checkout HEAD

# Clean up.
RUN yum -y remove git \
    && yum -y clean all \
    && rm -rf /var/cache/yum \
    && rm -rf /tmp/*

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
