# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Ondrej Kuznik
#    Copyright 2014 credativ ltd.
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

import logging
import xmlrpclib
from openerp.osv import orm, fields

from openerp.addons.connector.event import on_record_write
from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer

from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.magentoerpconnect.connector import get_environment
from openerp.addons.magentoerpconnect.product import chunks, magento_product_modified
from openerp.addons.magentoerpconnect.product import ProductInventoryExport as OriginalProductInventoryExport
from openerp.addons.magentoerpconnect.unit.backend_adapter import GenericAdapter
from openerp.addons.magentoerpconnect.unit.binder import MagentoModelBinder

_logger = logging.getLogger(__name__)


class magento_product_product(orm.Model):
    _inherit = 'magento.product.product'

    def _recompute_magento_qty_backend(self, cr, uid, backend, products,
                                       read_fields=None, context=None):
        """ Recompute the products quantity for one backend.

        If field names are passed in ``read_fields`` (as a list), they
        will be read in the product that is used in
        :meth:`~._magento_qty`.

        """
        if context is None:
            context = {}

        if backend.product_stock_field_id:
            stock_field = backend.product_stock_field_id.name
        else:
            stock_field = 'virtual_available'

        stock_level_obj = self.pool.get('magento.stock.levels')
        magento_location_obj = self.pool.get('magento.stock.location')

        magento_locations = magento_location_obj.search(cr, uid, [('backend_id', '=', backend.id), ('no_stock_sync', '=', False)], context=context)
        magento_locations = magento_location_obj.read(cr, uid, magento_locations, ['openerp_id'], context=context)

        product_fields = [stock_field]
        if read_fields:
            product_fields += read_fields

        to_export = False
        product_ids = [product['id'] for product in products]
        for magento_location in magento_locations:
            magento_location_id = magento_location['id']
            location_id = magento_location['openerp_id'][0]
            location_ctx = context.copy()
            location_ctx['location'] = location_id

            for chunk_ids in chunks(product_ids, self.RECOMPUTE_QTY_STEP):
                current_stock = stock_level_obj.stored_levels(cr, uid,
                                                              backend.id,
                                                              magento_location_id,
                                                              chunk_ids,
                                                              context=context)
                for product in self.read(cr, uid, chunk_ids, product_fields,
                                        context=location_ctx):
                    new_qty = self._magento_qty(cr, uid, product,
                                                         backend,
                                                         location_id,
                                                         stock_field,
                                                         context=location_ctx)
                    last_qty = current_stock.get(product['id'], {}).get('magento_qty', 0)
                    
                    if new_qty != last_qty:
                        to_export = True
                        if product['id'] in current_stock:
                            entry_id = current_stock[product['id']]['id']
                        else:
                            entry_id = stock_level_obj.create(cr, uid,
                                    {
                                        'backend_id': backend.id,
                                        'location_id': magento_location_id,
                                        'product_id': product['id'],
                                    }, context=context)
                        stock_level_obj.write(cr, uid, entry_id,
                                {
                                    'magento_qty': product[stock_field],
                                    'to_export': True,
                                },
                                context=context)

        stock_levels_to_export = stock_level_obj.search(cr, uid, [('backend_id', '=', backend.id), ('to_export', '=',True)], context=context)
        products_to_export = stock_level_obj.read(cr, uid, stock_levels_to_export, ['product_id'], context=context)
        for product in products_to_export:
            session = ConnectorSession(cr, uid, context=context)
            export_stock_levels.delay(session, 'magento.backend', backend.id, product['product_id'][0])

class magento_stock_location(orm.Model):
    _name = 'magento.stock.location'
    _inherit = 'magento.binding'
    _inherits = {'stock.location': 'openerp_id'}
    _description = 'Magento stock location'

    _columns = {
        'openerp_id': fields.many2one('stock.location',
                                      string='Stock Location',
                                      required=True,
                                      ondelete='restrict'),
        'no_stock_sync': fields.boolean(
            'No Stock Synchronization',
            required=False,
            help="Check this to exclude the location "
                 "from stock synchronizations."),
        }

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, magento_id)',
         "A location with the same ID on Magento already exists")
    ]

@magento
class MagentoStockLocationBinder(MagentoModelBinder):
    _model_name = [
        'magento.stock.location',
    ]

class magento_stock_levels(orm.Model):
    _name = 'magento.stock.levels'

    _columns = {
        'backend_id': fields.many2one('magento.backend',
            'Backend', required=True),
        'product_id': fields.many2one('magento.product.product',
            'Product', required=True),
        'location_id': fields.many2one('magento.stock.location',
            'Location', required=True),
        'magento_qty': fields.integer('Magento stock level'),
        'to_export': fields.boolean('To be exported', help="If system knows"
            " that the stock level has changed and needs to be exported"),
        }

    _sql_constraints = [
        ('magento_stock_levels_uniq', 'unique(backend_id, product_id, location_id)',
         "Only one stock level entry can exist for a backend")
    ]

    def stored_levels(self, cr, uid, backend, location, products=[], context=None):
        domain = [('backend_id', '=', backend), ('location_id', '=', location)]
        if hasattr(products, '__iter__'):
            domain.append(('product_id', 'in', list(products)))
        elif products:
            domain.append(('product_id', '=', products))

        ids = self.search(cr, uid, domain, context=context)
        stock_levels = self.read(cr, uid, ids, ['product_id', 'magento_qty'], context=context)

        res = {x['product_id'][0]: x for x in stock_levels}
        return res

@magento
class BackendAdapter(GenericAdapter):
    _model_name = 'magento.backend'

    def _call(self, method, arguments):
        try:
            return super(BackendAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Magento API
            # when the product does not exist
            if err.faultCode == 101:
                raise IDMissingInBackend
            else:
                raise

    def send_inventory(self, data):
        _logger.info('The following data is being sent to update Magento stock %s',data)
        return self._call('marceli_productstockupdate_api.update', data)


@magento
class ProductInventoryExport(ExportSynchronizer):
    _model_name = ['magento.backend']
    # FIXME: Modify to be based on model magento.product.product

    def _get_data(self, backend_id, product_id):
        ids = self.session.search('magento.stock.levels', [
                                        ('backend_id', '=', backend_id),
                                        ('to_export', '=', True),
                                        ('product_id', '=', product_id),
                                    ])
        stock_levels = self.session.read('magento.stock.levels', ids,
                            ['product_id', 'location_id', 'magento_qty'])

        for_binding = {}
        for entry in stock_levels:
            product_id, location_id, qty = entry['product_id'][0], entry['location_id'][0], entry['magento_qty']
            for_binding.setdefault(product_id, {})[location_id] = qty
            self.session.write('magento.stock.levels', entry['id'], {'to_export': False})

        product_binder = self.get_binder_for_model('magento.product.product')
        location_binder = self.get_binder_for_model('magento.stock.location')

        result = []
        for product, locations in for_binding.iteritems():
            product_id = product_binder.to_backend(product)
            product_entry = {}
            for location, qty in locations.iteritems():
                location_id = location_binder.to_backend(location)
                product_entry[location_id] = qty
            result += [(product_id, product_entry)]
        return result

    def run(self, backend_id, product_id):
        """ Export the inventory to a Magento backend """
        datas = self._get_data(backend_id, product_id)
        # FIXME: Modify _get_data to only return the result
        for data in datas:
            self.backend_adapter.send_inventory(data)

@on_record_write(model_names='magento.product.product', replacing=magento_product_modified)
def magento_product_modified_disable(*args, **kwargs):
    pass

@job
def export_stock_levels(session, model_name, backend_id, product_id):
    env = get_environment(session, model_name, backend_id)
    inventory_exporter = env.get_connector_unit(ProductInventoryExport)
    return inventory_exporter.run(backend_id, product_id)
