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
from openerp.tools.translate import _

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import JobError

from openerp.addons.connector_bots.unit.binder import BotsModelBinder
from openerp.addons.connector_bots.unit.backend_adapter import BotsCRUDAdapter
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector_bots.backend import bots
from openerp.addons.connector_bots.connector import get_environment

import json
import re

from openerp.addons.connector.event import on_record_create
from openerp.addons.connector_ecommerce.event import on_invoice_validated


class BotsAccountInvoice(orm.Model):
    _name = 'bots.account.invoice'
    _inherit = 'bots.binding'
    _inherits = {'account.invoice': 'openerp_id'}
    _description = 'Bots Invoice'

    _columns = {
        'openerp_id': fields.many2one('account.invoice',
                                      string='Invoice',
                                      required=True,
                                      ondelete='restrict'),
        'bots_sale_id': fields.many2one('bots.sale.order',
                                      string='Bots Sale Order',
                                      required=True,
                                      ondelete='restrict'),
    }

    _sql_constraints = [
        ('bots_invoice_uniq', 'unique(backend_id, bots_id)',
         'An invoice mapping with the same ID in Bots already exists.'),
    ]


@bots
class BotsAccountInvoiceBinder(BotsModelBinder):
    _model_name = [
            'bots.account.invoice',
        ]


@bots
class BotsAccountInvoiceAdapter(BotsCRUDAdapter):
    _model_name = 'bots.account.invoice'

    def export_invoice(self, invoice_id):
        MODEL = 'bots.account.invoice'
        FILENAME = 'account_invoice_%s.json'

        bots_invoice_obj = self.session.pool.get(MODEL)
        invoice_binder = self.get_binder_for_model(MODEL)

        invoice = bots_invoice_obj.browse(self.session.cr, self.session.uid, invoice_id)
        default_company_id = invoice.company_id.id
        if self.session.context and self.session.context.get('company_id'):
            default_company_id = self.session.context.get('company_id')
        ctx = (self.session.context or {}).copy()
        ctx.update({'company_id': default_company_id})

        invoice = bots_invoice_obj.browse(self.session.cr, self.session.uid, invoice_id, context=ctx)
        if invoice.bots_id:
            raise JobError(_('The Bots invoice %s already has an external ID. Will not export again.') % (invoice.id,))

        # Get a unique name for the invoice
        BOTS_ID_MAX_LEN = 16
        bots_id = re.sub(r'[\\/_-]', r'', invoice.name.upper())[:BOTS_ID_MAX_LEN]
        # Test if this ID is unique, if not increment it
        suffix_counter = 0
        existing_id = invoice_binder.to_openerp(bots_id)
        orig_bots_id = bots_id
        while existing_id:
            suffix_counter += 1
            bots_id = "%sS%s" % (orig_bots_id[:BOTS_ID_MAX_LEN-1-len(str(suffix_counter))], suffix_counter)
            existing_id = invoice_binder.to_openerp(bots_id)

        assert len(invoice.sale_ids) == 1  # Currently only compatible with one2one mapping between invoices and sales
        sale_order = invoice.sale_ids[0]

        party_data = {  # Single commented lines because "Ship to information" is currently disabled
                #'qual': 'ST', # Entity Identifier Code N101 {ST: Ship to, BS: Bill and ship to}
                ##'gln': value, # N104 UL (N103)
                ##'DUNS': value, # N104 1 (N103)
                ##'internalID': value, # N104 91 (N103)
                ##'externalID': value, # N104 92 (N103)
                #'name1': invoice.partner_id.name, # Ship to company name N102 (35 char max)
                #'name2': sale_order.partner_shipping_id.name, # Ship to contact name N201 (35 char max)
                #'address1': sale_order.partner_shipping_id.street, # Address line 1 N301 (35 char max)
                #'address2': sale_order.partner_shipping_id.street2, # Address line 2 N302 (35 char max)
                #'city': sale_order.partner_shipping_id.city, # City name N401 (char 2-20)
                #'pcode': sale_order.partner_shipping_id.zip, # Postal code N403 (char 2-15)
                #'state': sale_order.partner_shipping_id.state_id and sale_order.partner_shipping_id.state_id.name or False, # State or province N402 (char 2-2)
                #'country': sale_order.partner_shipping_id.country_id and sale_order.partner_shipping_id.country_id.name or False, # Country code N404 (char 2-3)
            }

        invoice_lines = []
        for line in invoice.lines:
            line_data = {
                    #'linenum': value, # IT101
                    'gtin': line.product_id.default_code or False,  # SKU IT109 (char 1-40)
                    'suart': line.product_id.default_code or False,  # SKU IT107 (char 1-40)
                    'byart': line.product_id.default_code or False,  # SKU IT111 (char 1-40)
                    'invqua': line.quantity,  # Quantity invoiced IT102
                    #'ordqua': value,
                    #'desc': value, # PID05
                    'price': line.price_unit,  # Unit price IT104 (e.g. 42 = 42.00)
                    #'ordunit': value,
                }
            invoice_lines.append(line_data)

        data = {
                'message': {
                        'partys': [party_data, ],
                        'lines': invoice_lines,
                        'sender': invoice.backend_id.name_from,  # QUERIES in grammar
                        'receiver': invoice.backend_id.name_to,  # QUERIES in grammar
                        #'testindicator': value,
                        #'docsrt': value,
                        'docnum': invoice.number,  # Invoice number BIG02
                        'docdtm': invoice.backend_id.datetime_convert(invoice.date_invoice),  # Invoice issue date BIG01 (CCYY-MM-DD HH:mm -> CCYYMMDD)
                        'deldtm': invoice.backend_id.datetime_convert(sale_order.picking_ids[0].date_done or False),  # Ship date DTM02 (CCYY-MM-DD HH:mm -> CCYYMMDD)
                        'ordernumber': sale_order.name,  # Order number BIG04
                        #'currency': value,
                        #'totalinvoiceamount': value, # TDS01
                        #'termsdiscountpercent': value, # ITD03
                        #'termsdiscountdaysdue': value, # ITD05
                        #'termsnetdays': value, # ITD07
                        #'totaltermsdiscount': value, # ITD08
                },
            }
        data = json.dumps(data, indent=4)

        filename_id = self._get_unique_filename(FILENAME)
        res = self._write(filename_id, data)
        return bots_id


@bots
class BotsAccountInvoiceExport(ExportSynchronizer):
    _model_name = ['bots.account.invoice']

    def run(self, invoice_id, new_cr=True):
        """
        Export invoices to Bots
        """
        self.backend_adapter.export_invoice(invoice_id, new_cr=new_cr)


@on_invoice_validated
def invoice_create_bindings(session, model_name, record_id):
    """
    Create a ``bots.account.invoice`` record. This record will then
    be exported to Bots.
    """
    invoice = session.browse(model_name, record_id)
    sales = invoice.sale_ids
    assert len(sales) == 1  # there should only be 1 bots sale for each invoice
    sale_binder = session.get_binder_for_model('bots.sale.order')
    bots_sale = sale_binder.to_backend(sales[0].id)
    session.create('bots.account.invoice',
                   {'backend_id': bots_sale.backend_id.id,
                    'openerp_id': invoice.id,
                    'bots_sale_id': bots_sale.id,
                    })


@on_record_create(model_names='bots.account.invoice')
def delay_export_account_invoice(session, model_name, record_id, vals):
    """
    Delay the job to export the bots invoice.
    """
    export_invoice.delay(session, model_name, record_id)


@job
def export_invoice(session, model_name, record_id):
    invoice = session.browse(model_name, record_id)
    backend_id = invoice.backend_id.id
    env = get_environment(session, model_name, backend_id)
    invoice_exporter = env.get_connector_unit(BotsAccountInvoiceExport)
    res = invoice_exporter.run(record_id)
    return res
