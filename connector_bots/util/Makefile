all: botsplugin

botsplugin: bots_odoo_dsv_plugin.zip

bots_odoo_dsv_plugin.zip:
	cd bots && \
	zip -r ../bots_odoo_dsv_plugin.zip * 

clean:
	rm -f bots_odoo_dsv_plugin.zip
