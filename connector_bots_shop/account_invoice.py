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
from datetime import datetime

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
        product_binder = self.get_binder_for_model('bots.product')

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

        if not len(invoice.sale_ids) == 1:  # Currently only compatible with one2one mapping between invoices and sales
            raise NotImplementedError('Only a single sale order per invoice is currently support')
        sale_order = invoice.sale_ids[0]

        partner_data = {
            "id": "P%d" % (invoice.partner_id.id),
            "name": invoice.partner_id.name or '',
            "street1": invoice.partner_id.street or '',
            "street2": invoice.partner_id.street2 or '',
            "city": invoice.partner_id.city or '',
            "zip": invoice.partner_id.zip or '',
            "country": invoice.partner_id.country_id and invoice.partner_id.country_id.code or '',
            "state": invoice.partner_id.state_id and invoice.partner_id.state_id.code or '',
            "phone": invoice.partner_id.phone or '',
            "fax": invoice.partner_id.fax or '',
            "email": invoice.partner_id.email or '',
            "language": invoice.partner_id.lang or '',
        }

        invoice_lines = []
        seq = 0
        for line in invoice.invoice_line:
            seq += 1
            line_data = {
                    'id': "%sS%s" % (bots_id, seq),
                    'seq': seq,
                    'product_sku': product_binder.to_backend(line.product_id.id) or False,
                    'product_qty': int(line.quantity),
                    'total': line.price_subtotal,
                    'desc': line.name,
                    'unit_price': line.price_unit,
                }
            invoice_lines.append(line_data)

        invoice_data = {
                    'id': bots_id,
                    'partner': partner_data,
                    'lines': invoice_lines,
                    'ref': invoice.number,
                    'date': invoice.backend_id.datetime_convert(invoice.date_invoice),
                    'sale': sale_order.name,
                    'sale_date': invoice.backend_id.datetime_convert(sale_order.picking_ids[0].date_done or ''),
                    'currency': invoice.currency_id.name,
                    'total': invoice.amount_total,
            }

        data = {
                'invoice': {
                        'invoices': [invoice_data,],
                        'header': [{
                                'state': 'done',
                                'partner_to': invoice.backend_id.name_to,
                                'partner_from': invoice.backend_id.name_from,
                                'date_msg': invoice.backend_id.datetime_convert(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')),
                            }],
                    },
                }
        data = json.dumps(data, indent=4)

        filename_id = self._get_unique_filename(FILENAME)
        res = self._write(filename_id, data)
        return bots_id


@bots
class BotsAccountInvoiceExport(ExportSynchronizer):
    _model_name = ['bots.account.invoice']

    def run(self, invoice_id):
        """
        Export invoices to Bots
        """
        self.backend_adapter.export_invoice(invoice_id)


@on_invoice_validated
def invoice_create_bindings(session, model_name, record_id):
    """
    Create a ``bots.account.invoice`` record. This record will then
    be exported to Bots.
    """
    invoice = session.browse(model_name, record_id)
    sale_ids = session.search('bots.sale.order', [('openerp_id', 'in', [x.id for x in invoice.sale_ids])])
    for sale in session.browse('bots.sale.order', sale_ids):
        if sale.backend_id.feat_invoice_exp:
            session.create('bots.account.invoice',
                        {'backend_id': sale.backend_id.id,
                            'openerp_id': invoice.id,
                            'bots_sale_id': sale.id,
                            })


@on_record_create(model_names='bots.account.invoice')
def delay_export_account_invoice(session, model_name, record_id, vals):
    """
    Delay the job to export the bots invoice.
    """
    export_invoice.delay(session, model_name, record_id, priority=30)


@job
def export_invoice(session, model_name, record_id):
    invoice = session.browse(model_name, record_id)
    backend_id = invoice.backend_id.id
    env = get_environment(session, model_name, backend_id)
    invoice_exporter = env.get_connector_unit(BotsAccountInvoiceExport)
    res = invoice_exporter.run(record_id)
    return res
