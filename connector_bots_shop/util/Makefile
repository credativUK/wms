all: botsplugin

botsplugin: bots_odoo_shop_x12.zip bots_odoo_base_shop_x12.zip

bots_odoo_shop_x12.zip:
	cd bots && \
	zip -r ../bots_odoo_shop_x12.zip *

bots_odoo_base_shop_x12.zip:
	cd ../../connector_bots/util/bots && \
	zip -r ../../../connector_bots_shop/util/bots_odoo_base_shop_x12.zip * && \
	cd ../../../connector_bots_shop/util/bots && \
	zip -gr ../bots_odoo_base_shop_x12.zip *

clean:
	rm -f bots_odoo_shop_x12.zip bots_odoo_base_shop_x12.zip
