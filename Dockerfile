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
        python-flask-xml-rpc \
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

ENV FLASK_CONFIG="/var/www/product-listings-manager/config.py"
RUN touch "$FLASK_CONFIG" \
    && chown 1001:1001 "$FLASK_CONFIG"

USER 1001
EXPOSE 5000

ENTRYPOINT [ "./server.sh" ]
