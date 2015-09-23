# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 credativ Ltd
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

from openerp.osv import fields, orm
from openerp.addons.connector.queue.job import job
from openerp.addons.connector_bots.connector import get_environment
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector.session import ConnectorSession

from openerp.addons.connector_bots.unit.backend_adapter import BotsCRUDAdapter
from openerp.addons.connector_bots.backend import bots

from .sale import import_sale_order

import json
from datetime import datetime


class BotsBackend(orm.Model):
    _inherit = 'bots.backend'

    _columns = {
        'feat_export_picking_out_when_done': fields.boolean('Export Complete Delivery Orders', help='Export delivery orders for this shop when they are complete'),
        'feat_inventory_exp': fields.boolean('Export Inventory', help='Export inventories for this shop'),
        'feat_invoice_exp': fields.boolean('Export Invoices', help='Export invoices for this shop'),
        'feat_sale_imp': fields.boolean('Import Sale Orders', help='Import sale orders for this shop'),
        'catalog_price_tax_included': fields.boolean('Prices include tax'),
        'lang_id': fields.many2one('res.lang', 'Language', required=True),  # TODO: Can the requirement be domain based?
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True),  # TODO: Can the requirement be domain based?
        'product_categ_ids': fields.many2many('product.category','prod_categ_bots_backend_rel','categ_id','backend_id', 'Product categories to export', help="Restrict exported inventory products by category.  Leave blank to include all."),
        'payment_method_id': fields.many2one('payment.method',
                                             'Payment Method for imported sale orders',
                                             ondelete='restrict'),
    }

    _defaults = {
        'feat_inventory_exp': False,
        'feat_invoice_exp': False,
        'feat_sale_imp': False,
        'catalog_price_tax_included': False,
    }

    _sql_constraints = [
        ('bots_single_export_delivery', 'CHECK (not (feat_picking_out and feat_export_picking_out_when_done))', 'A delivery order can either be exported when available or delivered - not both.'),
        ]

    def _scheduler_export_inventory(self, cr, uid, domain=None, new_cr=True, context=None):
        if not new_cr:
            self._bots_backend(cr, uid, self.export_inventory_test, domain=domain, context=context)
        else:
            self._bots_backend(cr, uid, self.export_inventory, domain=domain, context=context)

    def export_inventory_test(self, cr, uid, ids, context=None):
        return self.export_inventory(cr, uid, ids, new_cr=False, context=context)

    def export_inventory(self, cr, uid, ids, new_cr=True, context=None):
        """ Export inventory for backend """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        backends = self.browse(cr, uid, ids, context=context)
        for backend in backends:
            if backend.feat_inventory_exp:
                session = ConnectorSession(cr, uid, context=context)
                export_stock_levels.delay(session, 'bots.backend', backend.id, new_cr=new_cr)
        return True

    def _scheduler_import_sales(self, cr, uid, domain=None, new_cr=True, context=None):
        if not new_cr:
            self._bots_backend(cr, uid, self.import_sales_test, domain=domain, context=context)
        else:
            self._bots_backend(cr, uid, self.import_sales, domain=domain, context=context)

    def import_sales_test(self, cr, uid, ids, context=None):
        return self.import_sales(cr, uid, ids, new_cr=False, context=context)

    def import_sales(self, cr, uid, ids, new_cr=True, context=None):
        """ Import sale order from backend """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        backends = self.browse(cr, uid, ids, context=context)
        for backend in backends:
            if backend.feat_sale_imp:
                session = ConnectorSession(cr, uid, context=context)
                env = get_environment(session, 'bots.backend', backend.id)
                backend_adapter = BotsCRUDAdapter(env)
                FILENAME = r'^sale_.*\.json$'
                for file_id in backend_adapter._search(FILENAME):
                    import_sale_order.delay(session, 'bots.sale.order', file_id, backend.id, new_cr=new_cr)
        return True

@job
def export_stock_levels(session, model_name, backend_id, new_cr=True):
    env = get_environment(session, model_name, backend_id)
    backend_exporter = env.get_connector_unit(BotsBackendExport)
    backend_exporter.export_stock_levels(backend_id, new_cr=new_cr)
    return True


@bots
class BotsBackendExport(ExportSynchronizer):
    _model_name = ['bots.backend']

    def export_stock_levels(self, backend_id, new_cr=True):
        """
        Export stock levels to Bots
        """
        self.backend_adapter.export_stock_levels(backend_id, new_cr=new_cr)


@bots
class BotsBackendAdapter(BotsCRUDAdapter):
    _model_name = 'bots.backend'

    def export_stock_levels(self, backend_id, new_cr=True):
        """
        Export the stock levels to Bots
        """
        bots_backend_obj = self.session.pool.get('bots.backend')
        product_obj = self.session.pool.get('product.product')
        ctx = self.session.context.copy()
        backend_record = bots_backend_obj.browse(self.session.cr, self.session.uid, backend_id, context=ctx)
        ctx['location'] = [bots_warehouse.warehouse_id.lot_stock_id.id for bots_warehouse in backend_record.warehouse_ids]

        product_domain = [('exclude_from_bots_stock','=',False), ('default_code','!=',False)]
        categ_ids = [categ.id for categ in backend_record.product_categ_ids]
        if categ_ids:
            product_domain += ['|', ('categ_id', 'child_of', categ_ids), ('categ_ids', 'child_of', categ_ids)]

        product_ids_to_export = product_obj.search(self.session.cr, self.session.uid, product_domain, context=ctx)
        product_data_to_export = product_obj.read(self.session.cr, self.session.uid, product_ids_to_export, ['default_code', 'virtual_available'], context=ctx)

        product_datas = []
        for product in product_data_to_export:
            # TODO: How should zero and negative virtual quantities be handled?
            product_data = {
                'product_sku': product['default_code'],
                'quantity': product['virtual_available'],
                }
            product_datas.append(product_data)

        data = {
                'inventory': {
                    'products': product_datas,
                    'header': [{
                        'partner_to': backend_record.name_to,
                        'partner_from': backend_record.name_from,
                        'date_msg': backend_record.datetime_convert(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    }],
                },
            }

        FILENAME = 'stock_inventory_export_%s.json'
        filename_id = self._get_unique_filename(FILENAME)
        data = json.dumps(data, indent=4)
        res = self._write(filename_id, data)

        return True
