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

from openerp.osv import orm, fields

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import JobError, MappingError, NoExternalId
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )

from openerp.addons.connector_bots.unit.binder import BotsModelBinder
from openerp.addons.connector_bots.unit.backend_adapter import BotsCRUDAdapter, file_to_process
from openerp.addons.connector_bots.backend import bots
from openerp.addons.connector_bots.connector import get_environment, add_checkpoint

from openerp.addons.connector_ecommerce.unit.sale_order_onchange import (SaleOrderOnChange)

import openerp.addons.decimal_precision as dp

import json
import traceback


class SaleOrder(orm.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    _columns = {
            'bots_imported_json' : fields.text('Raw JSON data imported from BOTS'),
    }

class BotsSaleOrder(orm.Model):
    _name = 'bots.sale.order'
    _inherit = 'bots.binding'
    _inherits = {'sale.order': 'openerp_id'}
    _description = 'Bots Sale Order'

    _columns = {
        'openerp_id': fields.many2one('sale.order',
                                      string='Sale Order',
                                      required=True,
                                      ondelete='restrict'),
        'file_id': fields.char('Imported file')
    }

    _sql_constraints = [
        ('bots_sale_uniq', 'unique(backend_id, bots_id)',
         'A sale mapping with the same ID in Bots already exists.'),
    ]


@bots
class BotsSaleOrderBinder(BotsModelBinder):
    _model_name = [
            'bots.sale.order',
        ]


@bots
class BotsSaleOrderAdapter(BotsCRUDAdapter):
    _model_name = 'bots.sale.order'

    def import_sale_order(self, file_id, backend_id, new_cr=True):
        MODEL = 'bots.sale.order'
        bots_sale_obj = self.session.pool.get(MODEL)
        exceptions = []
        sale_ids = []
        try:
            with file_to_process(self.session, file_id[0], new_cr=new_cr) as f:
                bots_file_data = json.load(f)
                _cr = self.session.cr
                header_data = bots_file_data.get('sale', {}).get('header', {})
                for sale_data in bots_file_data.get('sale', {}).get('sales', []):
                    map_record = self.environment.get_connector_unit(BotsSaleOrderImportMapper).map_record(sale_data)
                    record_values = map_record.values()
                    sale_obj = self.session.pool.get('sale.order')
                    sale_id = sale_obj.create(self.session.cr, self.session.uid, record_values)
                    sale_ids.append(sale_id)
                    bots_sale_id = bots_sale_obj.create(self.session.cr, self.session.uid, {'file_id':file_id[1], 'openerp_id':sale_id, 'backend_id':backend_id})

                    # Create automatic payment for full order amount
                    sale_obj.automatic_payment(self.session.cr, self.session.uid, sale_id)
        except Exception, e:
            exception = "Exception %s when processing file %s: %s" % (e, file_id[1], traceback.format_exc())
            exceptions.append(exception)
        if exceptions:
            raise JobError('The following exceptions were encountered:\n\n%s' % ('\n\n'.join(exceptions),))
        return sale_ids


@bots
class BotsSaleOrderImport(ImportSynchronizer):
    _model_name = ['bots.sale.order']

    def run(self, file_id, backend_id, new_cr=True):
        """
        Import sale order from Bots
        """
        self.backend_adapter.import_sale_order(file_id, backend_id, new_cr=new_cr)


@bots
class BotsSaleOrderOnChange(SaleOrderOnChange):
    _model_name = 'bots.sale.order'


@bots
class BotsSaleOrderImportMapper(ImportMapper):
    _model_name = 'bots.sale.order'

    def _format_partner_name(self, name):
        return name

    def _get_partner_attributes(self, record):
        # Hook function for extending customer import with additional attributes
        # Return format: dict{field_name:field_value}
        return {}

    def name_duplicated(self, name):
        if self.session.search('sale.order', [('name','=',name)]):
            return True
        return False

    def finalize(self, map_record, values):
        onchange = self.get_connector_unit_for_model(SaleOrderOnChange)
        return onchange._play_order_onchange(values)

    @mapping
    def name(self, record):
        name = record['order']

        # Ensure unique order name - order will not be set to an automatic workflow if it was duplicated
        suffix_counter = 0
        duplicate_order_name_id = self.session.search('sale.order', [('name','=',name)])
        original_name = name
        while duplicate_order_name_id:
            suffix_counter += 1
            name = "%sS%s" % (original_name, suffix_counter)
            duplicate_order_name_id = self.session.search('sale.order', [('name','=',name)])
        return {'name': name}

    @mapping
    def date_order(self, record):
        date_order = record['order_date']
        return {'date_order': date_order}

    @mapping
    def data_summary(self, record):
        # Store 'record' on sale order so all imported data is available for reference
        return {'bots_imported_json': str(record)}

    @mapping
    def ship_date(self, record):
        ship_date = record.get('ship_date', False)
        if ship_date:
            return {'requested_delivery_date': ship_date}
        return {}

    @mapping
    def customer_and_addresses(self, record):
        partner_name = record.get('partner_name', False)
        partner_name = self._format_partner_name(partner_name)
        customer_email = record['partner_email']
        matching_customer_id = self.session.search('res.partner', [('email','=',customer_email)])
        address = False
        for partner_address in record['partner']:
            if partner_address.get('type', False) == 'delivery':
                address = partner_address
                break
        else:
            address = record['partner'] and record['partner'][0] or False
        if not address:
            raise MappingError('No address found for sale order')
        addr_country = False
        addr_state = False
        if address.get('country'):
            addr_country = self.session.search('res.country', [('code','=',address['country'])])
            addr_country = addr_country and addr_country[0] or False
        if address.get('state'):
            addr_state = self.session.search('res.country.state', [('code','=',address['state'])])
            addr_state = addr_state and addr_state[0] or False
        company_id = self.backend_record.shop_id.company_id and self.backend_record.shop_id.company_id.id or False
        if matching_customer_id:
            matching_customer_id = matching_customer_id[0]
            # TODO: Should the address search match by contact name and partner company name as well?
            matching_address_id = self.session.search('res.partner', [('country_id','=',addr_country),
                                                                      ('state_id','=',addr_state),
                                                                      ('zip','=',address.get('zip', False)),
                                                                      ('city','=',address.get('city', False)),
                                                                      ('street','=',address.get('address1', False)),
                                                                      ])
            if matching_address_id:
                shipping_invoice_address = matching_address_id[0]
            else:
                new_address_vals = {'parent_id': matching_customer_id,
                                    'name': partner_name,
                                    'street': address.get('address1', False),
                                    'street2': address.get('address2', False),
                                    'city': address.get('city', False),
                                    'state_id': addr_state,
                                    'zip': address.get('zip', False),
                                    'country_id': addr_country,
                                    'email': customer_email,
                                    'lang': self.backend_record.lang_id.code,
                                    'company_id': company_id,
                                    'customer': True,
                                    }
                shipping_invoice_address = self.session.create('res.partner', new_address_vals)
            return {'partner_id': matching_customer_id,
                    'partner_invoice_id': shipping_invoice_address,
                    'partner_shipping_id': shipping_invoice_address}
        else:
            new_partner_vals = {'name': partner_name,
                                'street': address.get('address1', False),
                                'street2': address.get('address2', False),
                                'city': address.get('city', False),
                                'state_id': addr_state,
                                'zip': address.get('zip', False),
                                'country_id': addr_country,
                                'email': customer_email,
                                'lang': self.backend_record.lang_id.code,
                                'company_id': company_id,
                                'customer': True,
                                }
            additional_partner_attributes = self._get_partner_attributes(record)
            new_partner_vals.update(additional_partner_attributes)
            new_partner_id = self.session.create('res.partner', new_partner_vals)
            return {'partner_id': new_partner_id,
                    'partner_invoice_id': new_partner_id,
                    'partner_shipping_id': new_partner_id}

    @mapping
    def sale_lines(self, record):
        product_obj = self.session.pool.get('product.product')
        pricelist_obj = self.session.pool.get('product.pricelist')
        order_lines = []
        for sale_line in record['line']:
            # TODO: Can handle UoM with sale_line['ordunit'] if they vary from single units
            pricelist_id = self.backend_record.shop_id.pricelist_id.id
            product_binder = self.get_binder_for_model('bots.product')
            product_id = product_binder.to_openerp(sale_line['product_sku'])
            if not product_id:
                raise NoExternalId("Product %s could not be found in OpenERP" % (sale_line['product_sku'],))
            product = product_obj.browse(self.session.cr, self.session.uid, product_id)
            product_qty = int(sale_line['qty'])
            if not self.backend_record.catalog_price_tax_included:
                list_values = pricelist_obj.price_get(self.session.cr, self.session.uid, [pricelist_id], product_id, product_qty)
                list_price = list_values[pricelist_id]
                if list_price:
                    # FIXME: Due to the precision of the discount we need to reverse engineer the list price in the SO
                    # line so we get the correct total price while keeping the list price as close as possible to the origional
                    discount_dp = dp.get_precision('Discount')(self.session.cr)[1]
                    discount = round((1 - float(sale_line['price'])/list_price) * 100.0, discount_dp)
                    list_price = float(sale_line['price']) / (1.0 - (discount / 100.0))
                else:
                    list_price = float(sale_line['price'])
                    discount = 0
            else:
                raise NotImplementedError('Only tax exclusive prices are implimented currently, disable "Prices include tax" in the backend')
            order_line = [0, 0, {'name': product.name,
                                 'product_id': product_id,
                                 'product_uom_qty': product_qty,
                                 'price_unit': list_price,
                                 'discount': discount,
                                 }]
            order_lines.append(order_line)
        return {'order_line': order_lines}

    @mapping
    def shop(self, record):
        shop_id = self.backend_record.shop_id.id
        return {'shop_id': shop_id}

    @mapping
    def pricelist(self, record):
        pricelist_id = self.backend_record.shop_id.pricelist_id.id
        return {'pricelist_id': pricelist_id}
    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def payment_method(self, record):
        method = self.backend_record.payment_method_id
        if self.name_duplicated(record['name']):
            # Prevent automatic workflow in case that imported order number is duplicated
            workflow_process_id = False
        else:
            workflow_process_id = method and method.workflow_process_id and method.workflow_process_id.id or False
        return {'payment_method_id': method and method.id or False,
                'workflow_process_id': workflow_process_id,
                }

    @mapping
    def user_id(self, record):
        """ Do not assign to a Salesperson otherwise sales orders are hidden
        for the salespersons (access rules)"""
        return {'user_id': False}


@job
def import_sale_order(session, model_name, file_id, backend_id, new_cr=True):
    env = get_environment(session, model_name, backend_id)
    sale_importer = env.get_connector_unit(BotsSaleOrderImport)
    res = sale_importer.run(file_id, backend_id, new_cr=new_cr)
    return res
