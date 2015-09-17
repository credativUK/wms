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
from openerp.addons.connector.exception import JobError
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )

from openerp.addons.connector_bots.unit.binder import BotsModelBinder
from openerp.addons.connector_bots.unit.backend_adapter import BotsCRUDAdapter, file_to_process
from openerp.addons.connector_bots.backend import bots
from openerp.addons.connector_bots.connector import get_environment, add_checkpoint

import json
import traceback


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
        try:
            with file_to_process(self.session, file_id[0], new_cr=new_cr) as f:
                bots_file_data = json.load(f)
                _cr = self.session.cr
                if bots_file_data.get('order', False):
                    record_data = bots_file_data['order']
                    map_record = self.environment.get_connector_unit(BotsSaleOrderImportMapper).map_record(record_data)
                    record_values = map_record.values()
                    sale_obj = self.session.pool.get('sale.order')
                    sale_id = sale_obj.create(self.session.cr, self.session.uid, record_values)
                    bots_sale_id = bots_sale_obj.create(self.session.cr, self.session.uid, {'file_id':file_id[1], 'openerp_id':sale_id, 'backend_id':backend_id})
                    
                    # Create automatic payment for full order amount
                    sale_obj.automatic_payment(self.session.cr, self.session.uid, sale_id)

                    add_checkpoint(self.session, 'sale.order', sale_id, backend_id)
                else:
                    exception = "'order' section of import data not found when processing file %s: %s" % (file_id[1], traceback.format_exc())
                    exceptions.append(exception)
        except Exception, e:
            exception = "Exception %s when processing file %s: %s" % (e, file_id[1], traceback.format_exc())
            exceptions.append(exception)
        if exceptions:
            raise JobError('The following exceptions were encountered:\n\n%s' % ('\n\n'.join(exceptions),))
        return sale_id


@bots
class BotsSaleOrderImport(ImportSynchronizer):
    _model_name = ['bots.sale.order']

    def run(self, file_id, backend_id, new_cr=True):
        """
        Import sale order from Bots
        """
        self.backend_adapter.import_sale_order(file_id, backend_id, new_cr=new_cr)


@bots
class BotsSaleOrderImportMapper(ImportMapper):
    _model_name = 'bots.sale.order'

    def name_duplicated(self, name):
        if self.session.search('sale.order', [('name','=',name)]):
            return True
        return False

    @mapping
    def name(self, record):
        name = record['header']['docnum']

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
        date_order = record['header']['docdtm']
        return {'date_order': date_order}

    @mapping
    def data_summary(self, record):
        # Add 'record' as note against sale order so all imported data is visible for reference
        return {'note': str(record)}

    @mapping
    def requested_ship_date(self, record):
        requested_ship_date = record['header'].get('requested_ship_date', False)
        if requested_ship_date:
            return {'requested_delivery_date': requested_ship_date}
        return {}

    @mapping
    def customer_and_addresses(self, record):
        customer_email = record['header']['customer_email']
        matching_customer_id = self.session.search('res.partner', [('email','=',customer_email)])
        addresses = record['header']['partys']
        assert len(addresses) == 1 # Ensure only one shipping/billing address linked with order
        address = addresses[0]
        addr_country = self.session.search('res.country', [('code','=',address['country'])])
        addr_country = addr_country and addr_country[0] or False
        addr_state = self.session.search('res.country.state', [('code','=',address['state'])])
        addr_state = addr_state and addr_state[0] or False
        company_id = self.backend_record.shop_id.company_id and self.backend_record.shop_id.company_id.id or False
        if matching_customer_id:
            # TODO: Should the address search match by contact name and partner company name as well?
            matching_address_id = self.session.search('res.partner', [('country_id','=',addr_country),
                                                                      ('state_id','=',addr_state),
                                                                      ('zip','=',address['pcode']),
                                                                      ('city','=',address['city']),
                                                                      ('street','=',address['address1']),
                                                                      ])
            if matching_address_id:
                shipping_invoice_address = matching_address_id
            else:
                new_address_vals = {'parent_id': matching_customer_id,
                                    'name': record['header']['customer_name'],
                                    'street': address['address1'],
                                    'street2': address['address2'],
                                    'city': address['city'],
                                    'state_id': addr_state,
                                    'zip': address['pcode'],
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
            new_partner_vals = {'name': record['header']['customer_name'],
                                'street': address['address1'],
                                'street2': address['address2'],
                                'city': address['city'],
                                'state_id': addr_state,
                                'zip': address['pcode'],
                                'country_id': addr_country,
                                'email': customer_email,
                                'lang': self.backend_record.lang_id.code,
                                'company_id': company_id,
                                'customer': True,
                                }
            new_partner_id = self.session.create('res.partner', new_partner_vals)
            return {'partner_id': new_partner_id,
                    'partner_invoice_id': new_partner_id,
                    'partner_shipping_id': new_partner_id}

    @mapping
    def sale_lines(self, record):
        order_lines = []
        for sale_line in record['header']['lines']:
            # TODO: Can handle UoM with sale_line['ordunit'] if they vary from single units
            pricelist_id = self.backend_record.shop_id.pricelist_id.id
            product_ids = self.session.search('product.product', [('default_code', '=', sale_line['product_sku'])])
            assert len(product_ids) == 1 # Ensure 1 and only 1 matching product
            product_id = product_ids[0]
            pricelist_obj = self.session.pool.get('product.pricelist')
            product_qty = sale_line['ordqua']
            if not self.backend_record.catalog_price_tax_included:
                list_values = pricelist_obj.price_get(self.session.cr, self.session.uid, [pricelist_id], product_id, product_qty)
                list_price = list_values[pricelist_id]
                if list_price:
                    discount = round(1 - sale_line['price']/list_price, 2)
                else:
                    discount = 0
            else:
                raise NotImplementedError # Tax inclusive prices are not implemented as line level tax information not imported in order to subtract
            order_line = [0, 0, {'product_id': product_id,
                                 'product_uom_qty': product_qty,
                                 'price_unit': list_price,
                                 'discount': discount,
                                 }]
            order_lines.append(order_line)
        return {'order_lines': order_lines}

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
        if self.name_duplicated(record['header']['docnum']):
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
