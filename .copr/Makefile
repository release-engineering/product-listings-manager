# Copr does not have Git available. Install it before anything else.
INSTALLER := $(shell [ -f /usr/bin/dnf ] && echo dnf || echo yum)
INSTALL_GIT := $(shell [ -f /usr/bin/git ] || $(INSTALLER) -y install git)

NAME = product-listings-manager
VERSION := $(shell git describe --tags --abbrev=0 --match 'v*' | sed 's/^v//')
COMMIT := $(shell git rev-parse HEAD)
SHORTCOMMIT := $(shell echo $(COMMIT) | cut -c1-7)
RELEASE := $(shell git describe --tags --match 'v*' \
             | sed 's/^[^-]*-//' \
             | sed 's/-/./')
NVR := $(NAME)-$(VERSION)-$(RELEASE).el7

# Copr will override this:
outdir = .


# Testing only
echo:
	echo COMMIT $(COMMIT)
	echo VERSION $(VERSION)
	echo RELEASE $(RELEASE)
	echo NVR $(NVR)

clean:
	rm -rf dist/
	rm -f $(NAME)-*.tar.gz
	rm -f $(NAME)-*.src.rpm

dist:
	[ -f /usr/bin/python ] || $(INSTALLER) -y install python \
	  && python setup.py sdist --dist-dir .

spec:
	sed $(NAME).spec.in \
          -e 's/@COMMIT@/$(COMMIT)/' \
          -e 's/@VERSION@/$(VERSION)/' \
          -e 's/@RELEASE@/$(RELEASE)/' \
          > $(NAME).spec

srpm: spec dist
	rpmbuild -bs $(NAME).spec \
          --define "_topdir ." \
          --define "_sourcedir ." \
          --define "_srcrpmdir $(outdir)" \
          --define "dist .el7"

.PHONY: dist spec srpm
