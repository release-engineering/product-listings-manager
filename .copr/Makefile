INSTALLER := $(shell [ -f /usr/bin/dnf ] && echo dnf || echo yum)
INSTALL_TITO := $(shell [ -f /usr/bin/tito ] || $(INSTALLER) -y install tito)

NAME = product-listings-manager

# Copr will override this:
outdir = .


srpm:
	tito build --test --srpm --output=$(outdir)

clean:
	rm -rf dist/
	rm -f $(NAME)-*.tar.gz
	rm -f $(NAME)-*.src.rpm

.PHONY: dist spec srpm
