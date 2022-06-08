FROM registry.centos.org/centos:8
LABEL \
    name="product-listings-manager" \
    vendor="product-listings-manager developers" \
    license="MIT" \
    build-date=""

# https://www.centos.org/centos-linux-eol/
RUN sed -i -e "s|mirrorlist=|#mirrorlist=|g" /etc/yum.repos.d/CentOS-* \
    && sed -i -e "s|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g" /etc/yum.repos.d/CentOS-* \
    && yum install -y epel-release \
    && yum -y install \
        --setopt=install_weak_deps=false \
        --setopt=tsflags=nodocs \
        git-core \
        python3 \
        python3-flask \
        python3-flask-sqlalchemy \
        python3-gunicorn \
        python3-koji \
        python3-pip \
        python3-psycopg2 \
        python3-sqlalchemy

RUN pip3 install \
        flask-restful==0.3.8

WORKDIR /var/www/product-listings-manager

# Restore working tree from current git commit in container.
COPY .git .git
RUN git reset --hard HEAD \
    && git checkout HEAD

# Clean up.
RUN yum -y remove git-core \
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
    "/usr/bin/gunicorn-3", \
    "--bind=0.0.0.0:5000", \
    "--access-logfile=-", \
    "--enable-stdio-inheritance", \
    "product_listings_manager.wsgi" \
    ]
