pwd := $(shell pwd)

all: base dsv_tests

base: bots_odoo_base_plugin.zip

dsv_tests: bots_odoo_dsv_plugin.zip

bots_odoo_base_plugin.zip:
	cd bots && \
	zip -r ../bots_odoo_base_plugin.zip * 

bots_odoo_dsv_plugin.zip: bots_odoo_base_plugin.zip $(shell find ./tests/dsv/)
	cp bots_odoo_base_plugin.zip bots_odoo_dsv_plugin.zip && \
	cd tests/dsv && \
	zip -r $(pwd)/bots_odoo_dsv_plugin.zip *

clean:
	rm -f bots_odoo_base_plugin.zip bots_odoo_dsv_plugin.zip
