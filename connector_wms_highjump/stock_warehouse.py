# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2014 credativ Ltd
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tools.translate import _
import logging
from openerp.osv import orm, fields
from .unit.backend_adapter import HighJumpCRUDAdapter
from .unit.import_synchronizer import HighJumpImportSynchronizer
from .connector import get_environment
from .backend import highjump
from openerp.addons.connector.queue.job import job

from collections import defaultdict

_logger = logging.getLogger(__name__)

@highjump
class WarehouseAdapter(HighJumpCRUDAdapter):
    _model_name = 'highjump.warehouse'

    def read(self, id, skus='ALL'):
        data = {
                'stockRequest': {
                    'StocksIn': [{
                        'StockIn': {
                            'ClientCode': self.highjump.username,
                            'SKU': skus,
                            },
                        },]
                    },
                }
        return self._call('GetStock', data)

    def report_stock(self, data):
        warehouse_map = {}
        product_map = {}
        product_obj = self.session.pool.get('product.product')
        # Reformat stock data by warehouse, then by product
        stock = defaultdict(dict)
        for r0 in data:
            for r1 in r0[1]:
                for r2 in r1[1]:
                    warehouse, sku, qty = r2['Warehouse'], r2['SKU'], r2['Quantity']
                    stock[warehouse][sku] = qty
        stock = dict(stock)
        # Map warehouse and product to OpenERP objects (if available)
        warehouse_binder = self.get_binder_for_model('highjump.warehouse')
        product_binder = self.get_binder_for_model('highjump.product.product')
        for warehouse, products in stock.iteritems():
            warehouse_map[warehouse] = warehouse_binder.to_openerp(warehouse)
            for product in products:
                if product not in product_map:
                    product_map[product] = product_binder.to_openerp(product)

        # Read stock levels for all products from WMS
        stock_oe = {}
        for warehouse, products in stock.iteritems():
            if not warehouse_map[warehouse]:
                continue
            wh_id = warehouse_map[warehouse]
            prod_ids = []
            stock_oe[wh_id] = {}
            for product in products:
                if not product_map[product]:
                    continue
                prod_ids.append(product_map[product])
            ctx = self.session.context.copy()
            ctx.update({'warehouse': wh_id})
            stock_res = product_obj.read(self.session.cr, self.session.uid, prod_ids, ['qty_available'], context=ctx)
            for r in stock_res:
                stock_oe[wh_id][r['id']] = r['qty_available']

        # Generate a difference between WMS and OE
        difference = []
        for wh, prods in stock.iteritems():
            for prod, qty in prods.iteritems():
                qty_oe = stock_oe.get(warehouse_map[wh], {}).get(product_map[prod])
                diff = {
                        'warehouse': wh,
                        'warehouse_id': warehouse_map[wh],
                        'product': prod,
                        'product_id': product_map[prod],
                        'wms_qty': qty,
                        'oe_qty': qty_oe,
                    }
                if qty_oe is None:
                    diff['message'] = _("Product does not exist in OpenERP")
                    difference.append(diff)
                elif qty_oe != qty:
                    diff['message'] = _("Product quantities do not match. Please check incoming deliveries and other stock moves.")
                    difference.append(diff)

        # Raise server action which has access to the three dictionaries
        if difference:
            ctx = self.session.context.copy()
            ctx.update({
                    'highjump_wms_qty': stock,
                    'highjump_oe_qty': stock_oe,
                    'highjump_diff_qty': difference,
                })
            template_id = self.session.pool.get('ir.model.data').get_object_reference(self.session.cr, self.session.uid, 'connector_wms_highjump', 'email_template_stock_difference')[1]
            self.session.pool.get('email.template').send_mail(self.session.cr, self.session.uid, template_id, self.environment.backend_record.id, force_send=True, context=ctx)

        return True

@highjump
class WarehouseImport(HighJumpImportSynchronizer):
    _model_name = ['highjump.warehouse']

    def run(self, skus='ALL'):
        """ Run the synchronization """
        data = self.backend_adapter.read(skus)
        _logger.info('Import stock levels for High Jump products %s returned %s', skus, data)
        self.backend_adapter.report_stock(data)

@job
def import_warehouse_stock_qty_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of stock from the WMS """
    if filters is None:
        filters = {'skus': 'ALL'}
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(WarehouseImport)
    importer.run(filters['skus'])
