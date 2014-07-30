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

import logging
from openerp.osv import orm, fields, osv
from .unit.binder import BotsModelBinder
from .unit.backend_adapter import BotsCRUDAdapter
from .backend import bots
from .connector import get_environment, add_checkpoint
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_create
from openerp.addons.connector_wms.event import on_picking_out_available, on_picking_in_available, on_picking_out_cancel, on_picking_in_cancel
from openerp.addons.connector.exception import MappingError, InvalidDataError, JobError, NoExternalId
from openerp.addons.connector.unit.synchronizer import (ImportSynchronizer,
                                                        ExportSynchronizer
                                                        )
from openerp import netsvc
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import pooler

import traceback
from datetime import datetime
import json
import re

_logger = logging.getLogger(__name__)

class StockPickingIn(orm.Model):
    _inherit = 'stock.picking.in'

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        exported = self.pool.get('bots.stock.picking.in').search(cr, SUPERUSER_ID, [('openerp_id', 'in', ids), ('move_lines.state', 'not in', ('done', 'cancel'))], context=context)
        if exported and cancel:
            exported_obj = self.pool.get('bots.stock.picking.in').browse(cr, uid, exported, context=context)
            exported = [x.id for x in exported_obj if not x.backend_id.feat_picking_in_cancel]
        if exported and doraise:
            raise osv.except_osv(_('Error!'), _('This picking has been exported to an external WMS and cannot be modified directly in OpenERP.'))
        return exported or False

    def cancel_assign(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, cancel=True, context=context)
        ctx = context and context.copy() or {}
        ctx.update({'from_picking': True})
        res = super(StockPickingIn, self).cancel_assign(cr, uid, ids, context=ctx)
        session = ConnectorSession(cr, uid, context=None)
        for id in ids:
            on_picking_in_cancel.fire(session, self._name, id)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, cancel=True, context=context)
        ctx = context and context.copy() or {}
        ctx.update({'from_picking': True})
        res = super(StockPickingIn, self).action_cancel(cr, uid, ids, context=ctx)
        return res

    def action_done(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockPickingIn, self).action_done(cr, uid, ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockPickingIn, self).unlink(cr, uid, ids, context=context)
        return res

class StockPickingOut(orm.Model):
    _inherit = 'stock.picking.out'

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        exported = self.pool.get('bots.stock.picking.out').search(cr, SUPERUSER_ID, [('openerp_id', 'in', ids), ('move_lines.state', 'not in', ('done', 'cancel'))], context=context)
        if exported and cancel:
            exported_obj = self.pool.get('bots.stock.picking.out').browse(cr, uid, exported, context=context)
            exported = [x.id for x in exported_obj if not x.backend_id.feat_picking_out_cancel]
        if exported and doraise:
            raise osv.except_osv(_('Error!'), _('This picking has been exported to an external WMS and cannot be modified directly in OpenERP.'))
        return exported or False

    def cancel_assign(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, cancel=True, context=context)
        ctx = context and context.copy() or {}
        ctx.update({'from_picking': True})
        res = super(StockPickingOut, self).cancel_assign(cr, uid, ids, context=ctx)
        session = ConnectorSession(cr, uid, context=None)
        for id in ids:
            on_picking_out_cancel.fire(session, self._name, id)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, cancel=True, context=context)
        ctx = context and context.copy() or {}
        ctx.update({'from_picking': True})
        res = super(StockPickingOut, self).action_cancel(cr, uid, ids, context=ctx)
        return res

    def action_done(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockPickingOut, self).action_done(cr, uid, ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockPickingOut, self).unlink(cr, uid, ids, context=context)
        return res

class StockPicking(orm.Model):
    _inherit = 'stock.picking'

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        exported = []
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.type == 'in':
                MODEL = 'bots.stock.picking.in'
                PARAM = 'feat_picking_in_cancel'
            elif pick.type == 'out':
                MODEL = 'bots.stock.picking.out'
                PARAM = 'feat_picking_out_cancel'
            else:
                continue
            exported.extend(self.pool.get(MODEL).search(cr, SUPERUSER_ID, [('openerp_id', 'in', ids), ('move_lines.state', 'not in', ('done', 'cancel'))], context=context))
            if exported and cancel:
                exported_obj = self.pool.get(MODEL).browse(cr, uid, exported, context=context)
                exported = [x.id for x in exported_obj if not getattr(x.backend_id, PARAM)]
            if exported and doraise:
                raise osv.except_osv(_('Error!'), _('This picking has been exported to an external WMS and cannot be modified directly in OpenERP.'))
        return exported or False

    def cancel_assign(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, cancel=True, context=context)
        ctx = context and context.copy() or {}
        ctx.update({'from_picking': True})
        res = super(StockPicking, self).cancel_assign(cr, uid, ids, context=ctx)
        session = ConnectorSession(cr, uid, context=None)
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.type == 'in':
                on_picking_in_cancel.fire(session, self._name, id)
            elif pick.type == 'out':
                on_picking_out_cancel.fire(session, self._name, id)
            else:
                continue
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, cancel=True, context=context)
        ctx = context and context.copy() or {}
        ctx.update({'from_picking': True})
        res = super(StockPicking, self).action_cancel(cr, uid, ids, context=ctx)
        return res

    def action_done(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockPicking, self).action_done(cr, uid, ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockPicking, self).unlink(cr, uid, ids, context=context)
        return res

class StockMove(orm.Model):
    _inherit = 'stock.move'

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        exported = False
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id and move.picking_id.type == 'out':
                exported = self.pool.get('stock.picking.out').bots_test_exported(cr, uid, [move.picking_id.id], doraise=doraise, cancel=cancel, context=context)
            elif move.picking_id and move.picking_id.type == 'in':
                exported = self.pool.get('stock.picking.in').bots_test_exported(cr, uid, [move.picking_id.id], doraise=doraise, cancel=cancel, context=context)
            if exported:
                return exported
        return False

    def cancel_assign(self, cr, uid, ids, context=None):
        context = context or {}
        if not context.get('from_picking') and self.bots_test_exported(cr, uid, ids, doraise=False, cancel=False, context=context):
            raise osv.except_osv(_('Error!'), _('This move has been exported to an external WMS and cannot unassigned directly. Unassign the picking.'))
        res = super(StockMove, self).cancel_assign(cr, uid, ids, context=context)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        context = context or {}
        if not context.get('from_picking') and self.bots_test_exported(cr, uid, ids, doraise=False, cancel=False, context=context):
            raise osv.except_osv(_('Error!'), _('This move has been exported to an external WMS and cannot be cancelled directly. Cancel the picking.'))
        res = super(StockMove, self).action_cancel(cr, uid, ids, context=context)
        return res

    def action_done(self, cr, uid, ids, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockMove, self).action_done(cr, uid, ids, context=context)
        return res

    def action_scrap(self, cr, uid, ids, product_qty, location_id, context=None):
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockMove, self).action_scrap(cr, uid, ids, product_qty, location_id, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self._test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockMove, self).unlink(cr, uid, ids, context=context)
        return res

class BotsStockInventory(orm.Model):
    _name = 'bots.stock.inventory'
    _inherit = 'bots.binding'
    _inherits = {'stock.inventory': 'openerp_id'}
    _description = 'Bots Inventory'

    _columns = {
        'openerp_id': fields.many2one('stock.inventory',
                                      string='Stock Inventory',
                                      required=True,
                                      ondelete='restrict'),
        'warehouse_id': fields.many2one('bots.warehouse',
                                      string='Bots Warehouse',
                                      required=True,
                                      ondelete='restrict'),
        }

    _sql_constraints = [
        ('bots_inventory_uniq', 'unique(backend_id, openerp_id)',
         'A Bots inventory already exists for this inventory for the same backend.'),
    ]

class BotsStockPickingOut(orm.Model):
    _name = 'bots.stock.picking.out'
    _inherit = 'bots.binding'
    _inherits = {'stock.picking.out': 'openerp_id'}
    _description = 'Bots Stock Picking Out'

    _columns = {
        'openerp_id': fields.many2one('stock.picking.out',
                                      string='Stock Picking Out',
                                      required=True,
                                      ondelete='restrict'),
        'warehouse_id': fields.many2one('bots.warehouse',
                                      string='Bots Warehouse',
                                      required=True,
                                      ondelete='restrict'),
        }

    _sql_constraints = [
        ('bots_picking_out_uniq', 'unique(backend_id, openerp_id)',
         'A Bots picking already exists for this picking for the same backend.'),
    ]

class BotsStockPickingIn(orm.Model):
    _name = 'bots.stock.picking.in'
    _inherit = 'bots.binding'
    _inherits = {'stock.picking.in': 'openerp_id'}
    _description = 'Bots Stock Picking In'

    _columns = {
        'openerp_id': fields.many2one('stock.picking.in',
                                      string='Stock Picking In',
                                      required=True,
                                      ondelete='restrict'),
        'warehouse_id': fields.many2one('bots.warehouse',
                                      string='Bots Warehouse',
                                      required=True,
                                      ondelete='restrict'),
        }

    _sql_constraints = [
        ('bots_picking_in_uniq', 'unique(backend_id, openerp_id)',
         'A Bots picking already exists for this picking for the same backend.'),
    ]

@bots
class BotsStockInventoryBinder(BotsModelBinder):
    _model_name = [
            'bots.stock.inventory',
        ]

@bots
class BotsStockPickingOutBinder(BotsModelBinder):
    _model_name = [
            'bots.stock.picking.out',
        ]

@bots
class BotsStockPickingInBinder(BotsModelBinder):
    _model_name = [
            'bots.stock.picking.in',
        ]

class StockPickingAdapter(BotsCRUDAdapter):
    _picking_type = None

    def create(self, picking_id):

        if self._picking_type == 'in':
            MODEL = 'bots.stock.picking.in'
            TYPE = 'in'
            FILENAME = 'picking_in_%s.json'
        elif self._picking_type == 'out':
            MODEL = 'bots.stock.picking.out'
            TYPE = 'out'
            FILENAME = 'picking_out_%s.json'
        else:
            raise NotImplementedError('Unable to adapt stock picking of type %s' % (self._picking_type,))

        product_binder = self.get_binder_for_model('bots.product.product')
        picking_binder = self.get_binder_for_model(MODEL)
        bots_picking_obj = self.session.pool.get(MODEL)
        picking_obj = self.session.pool.get('stock.picking')
        move_obj = self.session.pool.get('stock.move')
        bots_warehouse_obj = self.session.pool.get('bots.warehouse')
        wf_service = netsvc.LocalService("workflow")

        picking = bots_picking_obj.browse(self.session.cr, self.session.uid, picking_id)
        default_company_id = picking.warehouse_id.warehouse_id.company_id.id
        if self.session.context and self.session.context.get('company_id'):
             default_company_id = self.session.context.get('company_id')
        ctx = (self.session.context or {}).copy()
        ctx.update({'company_id': default_company_id})
        default_company = self.session.pool.get('res.company').browse(self.session.cr, self.session.uid, default_company_id, context=ctx)

        picking = bots_picking_obj.browse(self.session.cr, self.session.uid, picking_id, context=ctx)
        if self._picking_type == 'out':
            order_number = picking.sale_id and picking.sale_id.name or picking.name
            address = picking.partner_id or picking.sale_id and picking.sale_id.partner_shipping_id
        elif self._picking_type == 'in':
            order_number = picking.purchase_id and picking.purchase_id.name or picking.name
            address = picking.partner_id or picking.purchase_id and (picking.purchase_id.warehouse_id and picking.purchase_id.warehouse_id.partner_id or picking.purchase_id.dest_address_id)
        else:
            order_number = picking.name
            address = picking.partner_id

        if picking.bots_id:
            raise JobError(_('The Bots picking %s already has an external ID. Will not export again.') % (picking.id,))

        if not address:
            raise MappingError(_('Missing address when attempting to export Bots picking %s.') % (picking_id,))

        # Get a unique name for the picking
        bots_id = re.sub(r'[\\/_-]', r'', order_number.upper())
        # Test if this ID is unique, if not increment it
        suffix_counter = 0
        existing_id = picking_binder.to_openerp(bots_id)
        orig_bots_id = bots_id
        while existing_id:
            suffix_counter += 1
            bots_id = "%sS%s" % (orig_bots_id, suffix_counter)
            existing_id = picking_binder.to_openerp(bots_id)

        # Select which moves we will ship
        picking_complete = True
        moves_to_split = []
        order_lines = []
        seq = 1
        for move in picking.move_lines:
            if move.state != 'assigned':
                picking_complete = False
                moves_to_split.append(move.id)
                continue
            product_bots_id = move.product_id and product_binder.to_backend(move.product_id.id)
            if not product_bots_id:
                picking_complete = False
                moves_to_split.append(move.id)
                continue
            order_line = {
                    "id": "%sS%s" % (bots_id, seq),
                    "seq": seq,
                    "product": product_bots_id, 
                    "product_qty": int(move.product_qty),
                    "uom": move.product_uom.name,
                    "product_uos_qty": int(move.product_uos_qty),
                    "uos": move.product_uos.name,
                    "price_unit": move.price_unit \
                        or move.sale_line_id and move.sale_line_id.price_unit \
                        or move.purchase_line_id and move.purchase_line_id.price_unit \
                        or move.product_id.standard_price,
                    "price_currency": move.price_unit and move.price_currency_id.name \
                        or move.sale_line_id.price_unit and move.sale_line_id.company_id.currency_id.name \
                        or move.purchase_line_id.price_unit and move.purchase_line_id.company_id.currency_id.name \
                        or default_company.currency_id.name,
                }
            if move.product_id.volume:
                order_line['volume_net'] = move.product_id.volume
            if move.product_id.weight:
                order_line['weight'] = move.product_id.weight
            if move.product_id.weight_net:
                order_line['weight_net'] = move.product_id.weight_net
            if move.note:
                order_line['desc'] = move.note

            order_lines.append(order_line)

        if not order_lines:
            raise MappingError(_('Unable to export any order lines on export of Bots picking %s.') % (picking_id,))

        # Split picking depending on order policy
        if not picking_complete:
            picking_policy = picking.sale_id and picking.sale_id.picking_policy or 'direct'
            if picking_policy != 'direct':
                raise InvalidDataError(_('Unable to export picking %s. Picking policy does not allow it to be split and is not fully complete or some products are not mapped for export.') % (picking_id,))
            # Split the picking
            new_picking_id = picking_obj.copy(cr, uid, picking.openerp_id.id, context=ctx)
            move_obj.write(cr, uid, moves_to_split, {'picking_id': new_picking_id}, context=ctx)
            wf_service.trg_validate(self.session.uid, 'stock.picking', new_picking_id, 'button_confirm', self.session.cr)

        picking_data = {
                'id': bots_id,
                'name': bots_id,
                'order': bots_id,
                'state': 'new',
                'type': TYPE,
                'date': datetime.strptime(picking.min_date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y-%m-%d'),
                'partner':
                    {
                        "id": "P%d" % (picking.partner_id.id),
                        "name": picking.partner_id.name,
                        "street1": picking.partner_id.street,
                        "street2": picking.partner_id.street2,
                        "city": picking.partner_id.city,
                        "zip": picking.partner_id.zip,
                        "country": picking.partner_id.country_id and picking.partner_id.country_id.code or '',
                        "state": picking.partner_id.state_id and picking.partner_id.state_id.name or '',
                        "phone": picking.partner_id.phone,
                        "fax": picking.partner_id.fax,
                        "email": picking.partner_id.email,
                        "language": picking.partner_id.lang,
                    },
                'line': order_lines,
            }
        if picking.note:
            picking_data['desc'] = picking.note
        if picking.partner_id.vat:
            picking_data['partner']['vat'] = picking.partner_id.vat

        data = {
                'picking': {
                        'pickings': [picking_data,],
                        'header': [{
                                'type': TYPE,
                                'state': 'done',
                                'partner_to': picking.backend_id.name_to,
                                'partner_from': picking.backend_id.name_from,
                                'message_id': '0',
                                'date_msg': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                            }],
                    },
                }
        data = json.dumps(data, indent=4)

        filename_id = self._get_unique_filename(FILENAME)
        res = self._write(filename_id, data)
        return bots_id

    def delete(self, picking_id):

        if self._picking_type == 'in':
            MODEL = 'bots.stock.picking.in'
            TYPE = 'in'
            FILENAME = 'picking_in_%s.json'
        elif self._picking_type == 'out':
            MODEL = 'bots.stock.picking.out'
            TYPE = 'out'
            FILENAME = 'picking_out_%s.json'
        else:
            raise NotImplementedError('Unable to adapt stock picking of type %s' % (self._picking_type,))

        bots_picking_obj = self.session.pool.get(MODEL)

        picking = bots_picking_obj.browse(self.session.cr, self.session.uid, picking_id)
        if not picking.bots_id:
            raise JobError(_('The Bots picking %s is exported but does not yet have an external ID. Cannot be cancelled.') % (picking.id,))

        picking_data = {
                'id': picking.bots_id,
                'name': picking.bots_id,
                'order': picking.bots_id,
                'state': 'delete',
                'type': TYPE,
            }
        data = {
                'picking': {
                        'pickings': [picking_data,],
                        'header': [{
                                'type': TYPE,
                                'state': 'cancel',
                                'partner_to': picking.backend_id.name_to,
                                'partner_from': picking.backend_id.name_from,
                                'message_id': '0',
                                'date_msg': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                            }],
                    },
                }
        data = json.dumps(data, indent=4)

        filename_id = self._get_unique_filename(FILENAME)
        res = self._write(filename_id, data)
        return

@bots
class StockPickingOutAdapter(StockPickingAdapter):
    _model_name = 'bots.stock.picking.out'
    _picking_type = 'out'

@bots
class StockPickingInAdapter(StockPickingAdapter):
    _model_name = 'bot.stock.picking.in'
    _picking_type = 'in'

@bots
class WarehouseAdapter(BotsCRUDAdapter):
    _model_name = 'bots.warehouse'

    def get_picking_conf(self, picking_types):
        product_binder = self.get_binder_for_model('bots.product.product')
        picking_in_binder = self.get_binder_for_model('bots.stock.picking.in')
        picking_out_binder = self.get_binder_for_model('bots.stock.picking.out')
        bots_picking_in_obj = self.session.pool.get('bots.stock.picking.in')
        bots_picking_out_obj = self.session.pool.get('bots.stock.picking.out')
        picking_obj = self.session.pool.get('stock.picking')
        bots_warehouse_obj = self.session.pool.get('bots.warehouse')
        wf_service = netsvc.LocalService("workflow")
        exceptions = []

        FILENAME = r'^picking_conf_.*\.json$'
        file_ids = self._search(FILENAME)
        res = []
        ctx = self.session.context.copy()
        ctx['wms_bots'] = True

        for file_id in file_ids:
            try:
                _cr = pooler.get_db(self.session.cr.dbname).cursor()
                file_data, mutex = self._read(file_id)
                json_data = json.loads(file_data)

                for pickings in type(json_data) in (list, tuple) and json_data or [json_data,]:
                    for picking in pickings['orderconf']['shipment']:
                        if picking['type'] not in picking_types:
                            # We are not a picking we want to import, discared
                            continue

                        if picking['type'] == 'in':
                            picking_binder = picking_in_binder
                            bots_picking_obj = bots_picking_in_obj
                        elif picking['type'] == 'out':
                            picking_binder = picking_out_binder
                            bots_picking_obj = bots_picking_out_obj
                        else:
                            raise NotImplementedError("Unable to import picking of type %s" % (picking['type'],))

                        picking_id = picking_binder.to_openerp(picking['id'])
                        if not picking_id:
                            raise NoExternalId("Picking %s could not be found in OpenERP" % (picking['id'],))
                        stock_picking = bots_picking_obj.browse(_cr, self.session.uid, picking_id, context=ctx)

                        tracking_number = False
                        for tracking in picking.get('references', []):
                            # Get the first sane tracking reference
                            if tracking['type'] == 'shipping_ref' and picking['type'] == 'out' and tracking['id'] and tracking['id'] not in ('N/A',):
                                tracking_number = tracking['id']
                                break
                            if tracking['type'] == 'purchase_ref' and picking['type'] == 'in' and tracking['id'] and tracking['id'] not in ('N/A',):
                                tracking_number = tracking['id']
                                break
                            if tracking['id'] and tracking['id'] not in ('N/A',):
                                tracking_number = tracking['id']
                                break

                        if tracking_number:
                            bots_picking_obj.write(_cr, self.session.uid, picking_id, {'carrier_tracking_ref': tracking_number}, context=ctx)

                        if picking['confirmed'] not in ('Y', 'True', '1', True, 1):
                            # No more action needs to be taken, it is not yet delivered
                            continue

                        # Count products in the incoming file
                        prod_counts = {}
                        for line in picking['line']:
                            product_id = product_binder.to_openerp(line['product'])
                            if not product_id:
                                raise NoExternalId("Product %s could not be found in OpenERP" % (line['product'],))
                            prod_counts[product_id] = prod_counts.get(product_id, 0) + int(line['qty_real'])

                        # Orgainise into done, partial and extra
                        moves_part = []
                        moves_extra = []
                        for move in stock_picking.move_lines:
                            qty = prod_counts.get(move.product_id.id, 0)
                            if qty >= int(move.product_qty):
                                moves_part.append((move, int(move.product_qty)))
                                qty -= int(move.product_qty)
                            elif qty > 0 and qty < int(move.product_qty) and int(move.product_qty) > 0:
                                moves_part.append((move, qty))
                                qty = 0
                            else:
                                moves_part.append((move, 0))
                                qty = 0
                            prod_counts[move.product_id.id] = qty

                        for prod, qty in prod_counts.iteritems():
                            if qty > 0:
                                moves_extra.append((prod, qty))

                        # If extra, raise since we do not expect this
                        if moves_extra:
                            raise NotImplementedError("Unable to process unexpected incoming stock for %s: %s" % (picking['id'], moves_extra,))

                        # Prepare and complete the picking wizard
                        moves_to_ship = {}
                        for move, qty in moves_part:
                            moves_to_ship['move%s' % (move.id)] = {
                                'product_id': move.product_id.id,
                                'product_qty': qty,
                                'product_uom': move.product_uom.id,
                                'prodlot_id': move.prodlot_id.id,
                            }
                        split = picking_obj.do_partial(_cr, self.session.uid, [stock_picking.openerp_id.id], moves_to_ship, context=ctx)
                        stock_picking.refresh()

                        # If there is a backorder, we need to assert that the current picking remains available
                        # The backorder should be flagged for a checkpoint
                        if stock_picking.backorder_id:
                            if stock_picking.backorder_id.state != 'done' and stock_picking.state != 'assigned':
                                raise JobError('Error while creating backorder for picking %s imported from Bots' % (stock_picking.name,))
                            add_checkpoint(self.session, stock_picking.openerp_id._name, stock_picking.openerp_id.id, self.backend_record.id)

                        # Done, next line please
                        continue

                self._read_done(file_id, mutex)
                mutex = None
                _cr.commit()
            except Exception, e:
                # Log error then continue processing files
                exception = "%s: %s" % (e, traceback.format_exc())
                if file_id:
                    file = self.session.pool.get('bots.file').browse(_cr, SUPERUSER_ID, file_id, self.session.context)
                    exception = "File: %s\n%s" % (file.full_path, exception)
                exceptions.append(exception)
                _cr.rollback()
                continue
            finally:
                _cr.close()

        # If we hit any errors, fail the job with a list of all errors now
        if exceptions:
            raise JobError('The following exceptions were encountered:\n\n%s' % ('\n\n'.join(exceptions),))

        return res

    def get_stock_levels(self, warehouse_id):
        product_binder = self.get_binder_for_model('bots.product.product')
        inventory_binder = self.get_binder_for_model('bots.stock.inventory')
        bots_warehouse_obj = self.session.pool.get('bots.warehouse')
        product_obj = self.session.pool.get('product.product')
        inventory_obj = self.session.pool.get('stock.inventory')
        bots_inventory_obj = self.session.pool.get('bots.stock.inventory')
        exceptions = []

        FILENAME = r'^inventory_.*\.json$'
        file_ids = self._search(FILENAME)
        res = []
        warehouse = bots_warehouse_obj.browse(self.session.cr, self.session.uid, warehouse_id, self.session.context)


        for file_id in file_ids:
            try:
                _cr = pooler.get_db(self.session.cr.dbname).cursor()
                _session = ConnectorSession(_cr, self.session.uid, context=self.session.context)
                file_data, mutex = self._read(file_id)
                json_data = json.loads(file_data)
                inventory_lines = {}

                for inventory in type(json_data) in (list, tuple) and json_data or [json_data,]:
                    for line in inventory['inventory']['inventory_line']:
                        product_id = product_binder.to_openerp(line['product'])
                        if not product_id:
                            raise NoExternalId("Product %s could not be found in OpenERP" % (line['product'],))
                        # Check the stock level for this warehouse at this time
                        time = datetime.strptime(line['datetime'], '%Y-%m-%d %H:%M:%S')
                        qty = int(line['qty_available'])
                        assert inventory_lines.setdefault(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT), {}).get('product_id', None) == None, "Product %s, ID %s appears twice in the inventory for %s" % (line['product'], product_id, time)
                        inventory_lines.setdefault(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT), {})[product_id] = qty

                inventory_lines = sorted(inventory_lines.items(), key=lambda x: x[0])
                for time, products in inventory_lines:
                    inventory = {
                            'name': 'Bots - %s - %s' % (self.backend_record.name, time,),
                            'date': time,
                            'company_id': warehouse.warehouse_id.company_id.id,
                            'inventory_line_id': [],
                        }
                    for product_id, qty in products.iteritems():
                        location_id = warehouse.warehouse_id.lot_stock_id.id
                        ctx = {
                                'location': location_id,
                                #'to_date': time, # FIXME: Any recent inventories, even backdated, will not be considered since the date is always when it is done. Core bug or feature?
                            }
                        prod = product_obj.browse(_cr, self.session.uid, product_id, context=ctx)

                        if int(qty) == int(prod.qty_available):
                            # We match, no need to create an inventory line
                            continue

                        inventory_line = {
                                'product_id': product_id,
                                'location_id': location_id,
                                'product_qty': int(qty),
                                'product_uom': prod.uom_id.id, # We assume the qty is always in the standard UoM
                            }
                        inventory['inventory_line_id'].append([0, False, inventory_line])

                    if inventory['inventory_line_id']:
                        # We have a difference in inventory so we must create and validate a new inventory
                        inventory_id = inventory_obj.create(_cr, self.session.uid, inventory, context=self.session.context)
                        inventory_obj.action_confirm(_cr, self.session.uid, [inventory_id], context=self.session.context)
                        inventory_obj.action_done(_cr, self.session.uid, [inventory_id], context=self.session.context)
                        binding_id = bots_inventory_obj.create(_cr, self.session.uid,
                            {'backend_id': self.backend_record.id,
                            'openerp_id': inventory_id,
                            'warehouse_id': warehouse.id,
                            'bots_id': '%s %s' % (self.backend_record.name, time,),})
                        add_checkpoint(_session, 'stock.inventory', inventory_id, self.backend_record.id)

                self._read_done(file_id, mutex)
                mutex = None
                _cr.commit()
            except Exception, e:
                # Log error then continue processing files
                exception = "%s: %s" % (e, traceback.format_exc())
                if file_id:
                    file = self.session.pool.get('bots.file').browse(_cr, SUPERUSER_ID, file_id, self.session.context)
                    exception = "File: %s\n%s" % (file.full_path, exception)
                exceptions.append(exception)
                _cr.rollback()
                continue
            finally:
                _cr.close()

        # If we hit any errors, fail the job with a list of all errors now
        if exceptions:
            raise JobError('The following exceptions were encountered:\n\n%s' % ('\n\n'.join(exceptions),))

        return res


def picking_available(session, model_name, record_id, picking_type, location_type):
    warehouse_obj = session.pool.get('stock.warehouse')
    bots_warehouse_obj = session.pool.get('bots.warehouse')
    picking = session.browse(model_name, record_id)
    # Check to see if the picking should be exported to the WMS
    # If so create binding, else return
    if not picking.state == 'assigned': # Handle only deliveries which are assigned
        return
    if location_type == 'src':
        location_id = picking.location_id.id or picking.move_lines and picking.move_lines[0].location_id.id
    else:
        location_id = picking.location_dest_id.id or picking.move_lines and picking.move_lines[0].location_dest_id.id
    warehouse_ids = warehouse_obj.search(session.cr, session.uid, [('lot_stock_id', '=', location_id)])
    bots_warehouse_ids = bots_warehouse_obj.search(session.cr, session.uid, [('warehouse_id', 'in', warehouse_ids)])
    bots_warehouse = bots_warehouse_obj.browse(session.cr, session.uid, bots_warehouse_ids)
    for warehouse in bots_warehouse:
        backend_id = warehouse.backend_id
        if (picking_type == 'bots.stock.picking.out' and backend_id.feat_picking_out) or \
            (picking_type == 'bots.stock.picking.in' and backend_id.feat_picking_in):
            session.create(picking_type,
                            {'backend_id': backend_id.id,
                            'openerp_id': picking.id,
                            'warehouse_id': warehouse['id'],})

def picking_cancel(session, model_name, record_id, picking_type):
    warehouse_obj = session.pool.get('stock.warehouse')
    bots_warehouse_obj = session.pool.get('bots.warehouse')
    picking_ids = session.search(picking_type, [('openerp_id', '=', record_id)])
    pickings = session.browse(picking_type, picking_ids)
    for picking in pickings:
        export_picking_cancel.delay(session, picking_type, picking.id)

@bots
class BotsPickingExport(ExportSynchronizer):
    _model_name = ['bots.stock.picking.in',
                   'bots.stock.picking.out']

    def run(self, binding_id):
        """
        Export the picking to Bots
        """
        bots_id = self.backend_adapter.create(binding_id)
        self.binder.bind(bots_id, binding_id)

    def delete(self, binding_id):
        """
        Export the cancelled picking to Bots
        """
        self.backend_adapter.delete(binding_id)
        self.binder.unbind(binding_id)
        pass

@bots
class BotsWarehouseImport(ImportSynchronizer):
    _model_name = ['bots.warehouse']

    def import_picking_confirmation(self, picking_types=('in', 'out')):
        """
        Import the picking confirmation from Bots
        """
        self.backend_adapter.get_picking_conf(picking_types)

    def import_stock_levels(self, warehouse_id):
        """
        Import the picking confirmation from Bots
        """
        self.backend_adapter.get_stock_levels(warehouse_id)

@on_record_create(model_names='bots.stock.picking.out')
def delay_export_picking_out_available(session, model_name, record_id, vals):
    export_picking_available.delay(session, model_name, record_id)

@on_record_create(model_names='bots.stock.picking.in')
def delay_export_picking_in_available(session, model_name, record_id, vals):
    export_picking_available.delay(session, model_name, record_id)

@job
def export_picking_available(session, model_name, record_id):
    picking = session.browse(model_name, record_id)
    if picking.state == 'done' and session.search(model_name, [('backorder_id', '=', picking.openerp_id.id)]):
        # We are an auto-created back order completed - ignore this export
        return "Not creating backorder for auto-created done picking backorder %s" % (picking.name,)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(BotsPickingExport)
    res = picking_exporter.run(record_id)
    return res

@job
def export_picking_cancel(session, model_name, record_id):
    picking = session.browse(model_name, record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(BotsPickingExport)
    picking_exporter.delete(record_id)
    return True

@job
def import_picking_confirmation(session, model_name, record_id, picking_types):
    warehouse = session.browse(model_name, record_id)
    backend_id = warehouse.backend_id.id
    env = get_environment(session, model_name, backend_id)
    warehouse_importer = env.get_connector_unit(BotsWarehouseImport)
    warehouse_importer.import_picking_confirmation(picking_types=picking_types)
    return True

@job
def import_stock_levels(session, model_name, record_id):
    warehouse = session.browse(model_name, record_id)
    backend_id = warehouse.backend_id.id
    env = get_environment(session, model_name, backend_id)
    warehouse_importer = env.get_connector_unit(BotsWarehouseImport)
    warehouse_importer.import_stock_levels(record_id)
    return True

@on_picking_out_available
def picking_out_available(session, model_name, record_id):
    return picking_available(session, model_name, record_id, 'bots.stock.picking.out', location_type='src')

@on_picking_in_available
def picking_in_available(session, model_name, record_id):
    return picking_available(session, model_name, record_id, 'bots.stock.picking.in', location_type='dest')

@on_picking_out_cancel
def picking_out_cancel(session, model_name, record_id):
    return picking_cancel(session, model_name, record_id, 'bots.stock.picking.out')

@on_picking_in_cancel
def picking_in_cancel(session, model_name, record_id):
    return picking_cancel(session, model_name, record_id, 'bots.stock.picking.in')
