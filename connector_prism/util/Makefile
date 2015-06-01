pwd := $(shell pwd)

all: base prism_tests

base: bots_odoo_base_plugin.zip

prism_tests: bots_odoo_prism_plugin.zip

bots_odoo_base_plugin.zip:
	cd bots && \
	zip -r ../bots_odoo_base_plugin.zip * 

bots_odoo_prism_plugin.zip: bots_odoo_base_plugin.zip $(shell find ./tests/prism/)
	cp bots_odoo_base_plugin.zip bots_odoo_prism_plugin.zip && \
	cd tests/prism && \
	zip -r $(pwd)/bots_odoo_prism_plugin.zip *

clean:
	rm -f bots_odoo_base_plugin.zip bots_odoo_prism_plugin.zip
