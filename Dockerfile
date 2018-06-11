FROM centos:7
LABEL \
    name="product-listings-manager" \
    vendor="product-listings-manager developers" \
    license="MIT" \
    build-date=""

# product-listings-manager RPM path
ARG product_listings_manager_rpm

ARG cacert_url="undefined"

ARG config_path="/etc/product-listings-manager/config.py"
ARG dbname
ARG dbhost
ARG dbuser
ARG dbpasswd

COPY "$product_listings_manager_rpm" /tmp/product-listings-manager.rpm

RUN mkdir $(dirname $config_path) \
    && echo "DBNAME = '$dbname'" >> $config_path \
    && echo "DBHOST = '$dbhost'" >> $config_path \
    && echo "DBUSER = '$dbuser'" >> $config_path \
    && echo "DBPASSWD = '$dbpasswd'" >> $config_path

RUN yum install -y epel-release \
    && yum -y update \
    && yum -y install \
        "python-gunicorn" \
        "/tmp/product-listings-manager.rpm" \
    && yum -y clean all \
    && rm -f /tmp/*

RUN if [ "$cacert_url" != "undefined" ]; then \
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
