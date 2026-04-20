.PHONY: install update check

install:
	bash install.sh

update:
	git pull
	bash install.sh --update

check:
	bash install.sh --check
