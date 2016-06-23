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
from collections import Counter

from openerp.osv import orm, fields, osv
from openerp import netsvc, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import JobError, MappingError, InvalidDataError
from openerp.addons.connector.unit.synchronizer import ExportSynchronizer
from openerp.addons.connector.event import on_record_create
from openerp.addons.connector_wms.event import on_picking_out_available, on_picking_in_available, on_picking_out_cancel, on_picking_in_cancel

from openerp.addons.stock import stock_picking as stock_StockPicking

from .unit.binder import BotsModelBinder
from .unit.backend_adapter import BotsCRUDAdapter
from .backend import bots
from .connector import get_environment

import json
from datetime import datetime
import re
import openerp.addons.decimal_precision as dp

def get_bots_picking_ids(cr, uid, ids, ids_skipped, table, not_in_move_states, bots_id_condition, context={}):
    cr.execute("SELECT DISTINCT(bsp.id) FROM "+ table +" AS bsp " \
                "INNER JOIN stock_picking AS sp ON sp.id = bsp.openerp_id " \
                "LEFT JOIN stock_move AS sm ON sp.id = sm.picking_id " \
                "WHERE bsp.openerp_id IN %s " \
                "AND bsp.bots_override = False " \
                "AND bsp.id NOT IN %s " \
                "AND sm.state NOT IN %s " \
                "AND bsp.bots_id " + bots_id_condition , (tuple(ids), tuple(ids_skipped), tuple(not_in_move_states)))
    return [x[0] for x in cr.fetchall()]

class OrderPrio(orm.Model):
    _name = 'order.prio'

    _columns = {
        'name' : fields.char('Name', required=True),
        'code' : fields.char('Code', required=True, size=1),
    }

    _sql_constraints = [
        ('prio_code_uniq', 'unique(code)',
         'A prio with this code already exists in the system.'),
    ]

class StockPickingIn(orm.Model):
    _inherit = 'stock.picking.in'

    # we redefine the min_date field, so these functions have to exist
    def get_min_max_date(self, *args, **kwargs):
        return super(StockPickingIn, self).get_min_max_date(*args, **kwargs)

    def _set_minimum_date(self, *args, **kwargs):
        return super(StockPickingIn, self)._set_minimum_date(*args, **kwargs)

    def _get_stock_move_changes(self, *args, **kwargs):
        # self is a 'stock.move' object, so we have no way of finding out where
        # we are in the inheritance DAG
        self = self.pool.get('stock.picking.in')
        return stock_StockPicking._get_stock_move_changes(self, *args, **kwargs)

    _columns = {
            'bots_customs': fields.boolean('Bonded Goods', help='If this picking is subject to duties.', states={'done':[('readonly', True)], 'cancel':[('readonly',True)], 'assigned':[('readonly',True)]}),
            'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', readonly=True, states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},),
            'partner_id': fields.many2one('res.partner', 'Destination Address ', help="Optional address where goods are to be delivered, specifically used for allotment", readonly=True, states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},),
            'min_date': fields.function(
                get_min_max_date,
                fnct_inv=_set_minimum_date, multi='min_max_date',
                store={
                    'stock.move': (
                        _get_stock_move_changes,
                        ['date_expected', 'picking_id'], 10,
                    )
                },
                type='datetime', string='Scheduled Time', select=True,
                readonly=True, states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},
                help="Scheduled time for the shipment to be processed"
            ),
            'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=128),
        }

    _defaults = {
            'bots_customs':  lambda *a: False,
        }

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        bots_picking_obj = self.pool.get('bots.stock.picking.in')
        backend_obj = self.pool.get('bots.backend')
        res = {}
        ids_skipped = self.pool.get('stock.picking').bots_skip_ids(cr, uid, ids, type='in', context=context)

        ids_pending = get_bots_picking_ids(cr, uid, ids, ids_skipped, table='bots_stock_picking_in', not_in_move_states=('done', 'cancel'), bots_id_condition='IS NULL', context=context)
        states = ['cancel']
        if doraise:
            states.append('done')
        ids_exported = get_bots_picking_ids(cr, uid, ids, ids_skipped, table='bots_stock_picking_in', not_in_move_states=states, bots_id_condition='IS NOT NULL', context=context)

        ids_all = ids_pending + ids_exported
        if ids_all and cancel:
            backend_ids = backend_obj.search(cr, SUPERUSER_ID, [('feat_picking_in_cancel', '=', 'export')], context=context)
            exported_pickings = bots_picking_obj.read(cr, uid, ids_all, ['bots_id', 'backend_id'], context=context)
            ids_all = [x['id'] for x in exported_pickings if not x['bots_id'] or not x['backend_id'] in backend_ids]
        if ids_all and doraise:
            raise osv.except_osv(_('Error!'), _('This picking has been exported, or is pending export, to an external WMS and cannot be modified directly in OpenERP.'))
        if ids_exported:
            res['exported'] = ids_exported
        if ids_pending:
            res['pending'] = ids_pending
        return res

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

    # we redefine the min_date field, so these functions have to exist
    def get_min_max_date(self, *args, **kwargs):
        return super(StockPickingOut, self).get_min_max_date(*args, **kwargs)

    def _set_minimum_date(self, *args, **kwargs):
        return super(StockPickingOut, self)._set_minimum_date(*args, **kwargs)

    def _get_stock_move_changes(self, *args, **kwargs):
        # self is a 'stock.move' object, so we have no way of finding out where
        # we are in the inheritance DAG
        self = self.pool.get('stock.picking.out')
        return stock_StockPicking._get_stock_move_changes(self, *args, **kwargs)

    _columns = {
            'bots_customs': fields.boolean('Bonded Goods', help='If this picking is subject to duties.', states={'done':[('readonly', True)], 'cancel':[('readonly',True)], 'assigned':[('readonly',True)]}),
            'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', readonly=True, states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},),
            'partner_id': fields.many2one('res.partner', 'Destination Address ', help="Optional address where goods are to be delivered, specifically used for allotment", readonly=True, states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},),
            'min_date': fields.function(
                get_min_max_date,
                fnct_inv=_set_minimum_date, multi='min_max_date',
                store={
                    'stock.move': (
                        _get_stock_move_changes,
                        ['date_expected', 'picking_id'], 10,
                    )
                },
                type='datetime', string='Scheduled Time', select=True,
                readonly=True, states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},
                help="Scheduled time for the shipment to be processed"
            ),
            'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=128),
            'prio_id' : fields.many2one('order.prio', 'Priority', help='The priority code to assign to this picking. If blank, will default to \'4\'.', readonly=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        }

    def _get_default_prio(self, cr, uid, context=None):
        return self.pool.get('stock.picking')._get_default_prio(cr, uid, context=context)

    _defaults = {
            'bots_customs':  lambda *a: False,
            'prio_id': _get_default_prio,
        }

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        bots_picking_obj = self.pool.get('bots.stock.picking.out')
        backend_obj = self.pool.get('bots.backend')
        res = {}
        ids_skipped = self.pool.get('stock.picking').bots_skip_ids(cr, uid, ids, type='out', context=context)

        ids_pending = get_bots_picking_ids(cr, uid, ids, ids_skipped, table='bots_stock_picking_out', not_in_move_states=('done', 'cancel'), bots_id_condition='IS NULL', context=context)
        states = ['cancel']
        if doraise:
            states.append('done')
        ids_exported = get_bots_picking_ids(cr, uid, ids, ids_skipped, table='bots_stock_picking_out', not_in_move_states=states, bots_id_condition='IS NOT NULL', context=context)

        ids_all = ids_pending + ids_exported
        if ids_all and cancel:
            backend_ids = backend_obj.search(cr, SUPERUSER_ID, [('feat_picking_out_cancel', '=', 'export')], context=context)
            exported_pickings = bots_picking_obj.read(cr, uid, ids_all, ['bots_id', 'backend_id'], context=context)
            ids_all = [x['id'] for x in exported_pickings if not x['bots_id'] or not x['backend_id'] in backend_ids]
        if ids_all and doraise:
            raise osv.except_osv(_('Error!'), _('This picking has been exported, or is pending export, to an external WMS and cannot be modified directly in OpenERP.'))
        if ids_exported:
            res['exported'] = ids_exported
        if ids_pending:
            res['pending'] = ids_pending
        return res

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

    _columns = {
            'bots_customs': fields.boolean('Bonded Goods', help='If this picking is subject to duties.', states={'done':[('readonly', True)], 'cancel':[('readonly',True)], 'assigned':[('readonly',True)]}),
            'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=128),
            'prio_id' : fields.many2one('order.prio', 'Priority', help='The priority code to assign to this picking. If blank, will default to \'4\'.', readonly=True, states={'draft':[('readonly',False)],'confirmed':[('readonly',False)]}),
        }

    def _get_default_prio(self, cr, uid, context=None):
        # On deployment, the initial data is not populated at this point.
        # Since the default that we want is assumed if blank anyway, it
        # is safe to leave the default values empty (though '4' will
        # default in the future to avoid ambiguity).
        if context.get('module') == 'connector_bots':
            return None
        prio_obj = self.pool.get('order.prio')
        prio_ids = prio_obj.search(cr, uid, [('code', '=', '4')], context=context)
        if not prio_ids:
            raise osv.except_osv( _('Error: Cannot assign default prio of \'4\' to the order'),
                                  _('No such prio defined in system'),
                                )
        # Safe - prio codes are unique system-wide (SQL constraint)
        return prio_ids[0]

    _defaults = {
            'bots_customs':  lambda *a: False,
            'prio_id': _get_default_prio,
        }

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['bots_test_backorder_override'] = True
        return super(StockPicking, self).do_partial(cr, uid, ids, partial_datas, context=ctx)

    def bots_skip_ids(self, cr, uid, ids, type='in', context=None):
        ''' Skip checking of any pickings which are backorders of overriden bindings '''
        ids_skipped = []
        if context.get('bots_test_backorder_override'):
            if type == 'in':
                picking_obj = self.pool.get('stock.picking.in')
                bots_picking_obj = self.pool.get('bots.stock.picking.in')
            else:
                picking_obj = self.pool.get('stock.picking.out')
                bots_picking_obj = self.pool.get('bots.stock.picking.out')
            for id in ids:
                backorder_id = picking_obj.search(cr, SUPERUSER_ID, [('backorder_id', '=', id)], context=context)
                binding_id = bots_picking_obj.search(cr, SUPERUSER_ID, [('openerp_id', '=', id), ('bots_override', '=', False)], context=context)
                if backorder_id and binding_id:
                    backorder_binding_id = bots_picking_obj.search(cr, SUPERUSER_ID, [('openerp_id', '=', backorder_id[0]), ('bots_override', '=', True)], context=context)
                    if backorder_binding_id:
                        ids_skipped.append(binding_id[0])
        return ids_skipped or [0]

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        exported = []
        pending = []
        backend_obj = self.pool.get('bots.backend')
        for pick_read in self.read(cr, uid, ids, ['type'], context=context):
            picking_type = pick_read['type']
            if picking_type == 'in':
                MODEL = 'bots.stock.picking.in'
                TABLE = 'bots_stock_picking_in'
                PARAM = 'feat_picking_in_cancel'
            elif picking_type == 'out':
                MODEL = 'bots.stock.picking.out'
                TABLE = 'bots_stock_picking_out'
                PARAM = 'feat_picking_out_cancel'
            else:
                continue
            ids_skipped = self.bots_skip_ids(cr, uid, ids, type=picking_type, context=context)

            ids_pending = get_bots_picking_ids(cr, uid, ids, ids_skipped, table=TABLE, not_in_move_states=('done', 'cancel'), bots_id_condition='IS NULL', context=context)
            states = ['cancel']
            if doraise:
                states.append('done')
            ids_exported = get_bots_picking_ids(cr, uid, ids, ids_skipped, table=TABLE, not_in_move_states=states, bots_id_condition='IS NOT NULL', context=context)

            ids_all = ids_pending + ids_exported
            if ids_all and cancel:
                backend_ids = backend_obj.search(cr, SUPERUSER_ID, [(PARAM, '=', 'export')], context=context)
                exported_pickings = self.pool.get(MODEL).read(cr, uid, ids_all, ['bots_id', 'backend_id'], context=context)
                ids_all = [x['id'] for x in exported_pickings if not x['bots_id'] or not x['backend_id'] in backend_ids]
            if ids_all and doraise:
                raise osv.except_osv(_('Error!'), _('This picking has been exported, or is pending export, to an external WMS and cannot be modified directly in OpenERP.'))
            exported.extend(ids_exported)
            pending.extend(ids_pending)
        res = {}
        if exported:
            res['exported'] = exported
        if pending:
            res['pending'] = pending
        return res

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

    def _bots_test_exported(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        # Group moves by picking to improve performance
        picking_dict = {}
        for move_read in self.read(cr, uid, ids, ['picking_id'], context=context):
            picking_id = move_read['picking_id'] and move_read['picking_id'][0]
            picking_dict.setdefault(picking_id, []).append(move_read['id'])
        for picking_id, move_ids in picking_dict.iteritems():
            if picking_id and move_ids:
                exported = self.bots_test_exported(cr, uid, move_ids, doraise=False, cancel=False, context=context).get('exported', False) and True or False
                for move_id in move_ids:
                    res[move_id] = exported
            elif not picking_id:
                for move_id in move_ids:
                    res[move_id] = self.bots_test_exported(cr, uid, [move_id], doraise=False, cancel=False, context=context).get('exported', False) and True or False
        return res

    _columns = {
        'pick_state': fields.related(
                'picking_id', 'state',
                type='char',
                readonly=True,
                string='Picking state',
            ),
        'bots_exported': fields.function(_bots_test_exported, type='boolean', string='Exported to 3PL', readonly=True, help="Has this move been exported to 3PL/Bots"),
    }

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        exported = False
        pickings = []
        for move_read in self.read(cr, uid, ids, ['picking_id', 'type'], context=context):
            picking_id = move_read['picking_id'] and move_read['picking_id'][0]
            picking_type = move_read['type']
            if (picking_id, picking_type) not in pickings:
                pickings.append((picking_id, picking_type))
        for picking_id, picking_type in pickings:
            if picking_type == 'out':
                exported = self.pool.get('stock.picking.out').bots_test_exported(cr, uid, [picking_id], doraise=doraise, cancel=cancel, context=context)
            elif picking_type == 'in':
                exported = self.pool.get('stock.picking.in').bots_test_exported(cr, uid, [picking_id], doraise=doraise, cancel=cancel, context=context)
            if exported:
                return exported
        return {}

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
        self.bots_test_exported(cr, uid, ids, doraise=True, context=context)
        res = super(StockMove, self).unlink(cr, uid, ids, context=context)
        return res

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
        'bots_override': fields.boolean('Override Bots Restrictions', help='Allow all normal Bots constraints to be ignored, eg when completing or cancelling.'),
        }

    _sql_constraints = [
        ('bots_picking_out_uniq', 'unique(backend_id, openerp_id)',
         'A Bots picking already exists for this picking for the same backend.'),
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'bots_id'], context=context)
        res = []
        for record in reads:
            if record['bots_id']:
                name = record['bots_id']
            else:
                name = "*%s" % (record['name'],)
            res.append((record['id'], name))
        return res

    def reexport_order(self, cr, uid, ids, context=None):
        session = ConnectorSession(cr, uid, context=context)
        for id in ids:
            export_picking.delay(session, self._name, id)
        return True

    def reexport_cancel(self, cr, uid, ids, context=None):
        session = ConnectorSession(cr, uid, context=context)
        for id in ids:
            picking = self.browse(cr, uid, id, context=context)
            if picking.backend_id.feat_picking_out_cancel == 'export':
                export_picking_cancel.delay(session, self._name, id)
        return True

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
        'bots_override': fields.boolean('Override Bots Restrictions', help='Allow all normal Bots constraints to be ignored, eg when completing or cancelling.'),
        }

    _sql_constraints = [
        ('bots_picking_in_uniq', 'unique(backend_id, openerp_id)',
         'A Bots picking already exists for this picking for the same backend.'),
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'bots_id'], context=context)
        res = []
        for record in reads:
            if record['bots_id']:
                name = record['bots_id']
            else:
                name = "*%s" % (record['name'],)
            res.append((record['id'], name))
        return res

    def reexport_order(self, cr, uid, ids, context=None):
        session = ConnectorSession(cr, uid, context=context)
        for id in ids:
            export_picking.delay(session, self._name, id)
        return True

    def reexport_cancel(self, cr, uid, ids, context=None):
        session = ConnectorSession(cr, uid, context=context)
        for id in ids:
            picking = self.browse(cr, uid, id, context=context)
            if picking.backend_id.feat_picking_in_cancel == 'export':
                export_picking_cancel.delay(session, self._name, id)
        return True

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

    def _prepare_create_data(self, picking_id):
        def _find_pricelist_cost(cr, uid, pl_id, prod_id, partner, uom, date, context=None):
            pl_obj = self.session.pool.get('product.pricelist')
            price = pl_obj.price_get(cr, uid, [pl_id], prod_id, 1.0, partner, {
                'uom' : uom,
                'date' : date,
                })[pl_id]
            return price

        if self._picking_type == 'in':
            MODEL = 'bots.stock.picking.in'
            TYPE = 'in'
            FILENAME = 'picking_in_%s.json'
            ALLOWED_STATES = ('waiting', 'confirmed', 'assigned', 'done')
        elif self._picking_type == 'out':
            MODEL = 'bots.stock.picking.out'
            TYPE = 'out'
            FILENAME = 'picking_out_%s.json'
            ALLOWED_STATES = ('assigned', 'done')
        else:
            raise NotImplementedError('Unable to adapt stock picking of type %s' % (self._picking_type,))

        product_binder = self.get_binder_for_model('bots.product')
        picking_binder = self.get_binder_for_model(MODEL)
        bots_picking_obj = self.session.pool.get(MODEL)
        picking_obj = self.session.pool.get('stock.picking')
        move_obj = self.session.pool.get('stock.move')
        currency_obj = self.session.pool.get('res.currency')
        tax_obj = self.session.pool.get('account.tax')
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
            incoterm = picking.sale_id and picking.sale_id.incoterm and picking.sale_id.incoterm.code or ""
        elif self._picking_type == 'in':
            order_number = picking.purchase_id and picking.purchase_id.name or picking.name
            address = picking.partner_id or picking.purchase_id and (picking.purchase_id.warehouse_id and picking.purchase_id.warehouse_id.partner_id or picking.purchase_id.dest_address_id)
            incoterm = picking.purchase_id and picking.purchase_id.incoterm_id and picking.purchase_id.incoterm_id.code or ""
        else:
            order_number = picking.name
            address = picking.partner_id
            incoterm = ""

        if picking.bots_id:
            raise JobError(_('The Bots picking %s already has an external ID. Will not export again.') % (picking.id,))

        if not address:
            raise MappingError(_('Missing address when attempting to export Bots picking %s.') % (picking_id,))

        # Get a unique name for the picking
        BOTS_ID_MAX_LEN = 16
        bots_id = re.sub(r'[\\/_-]', r'', order_number.upper())[:BOTS_ID_MAX_LEN]
        # Test if this ID is unique, if not increment it
        suffix_counter = 0
        existing_id = picking_binder.to_openerp(bots_id)
        orig_bots_id = bots_id
        while existing_id:
            suffix_counter += 1
            bots_id = "%sS%s" % (orig_bots_id[:BOTS_ID_MAX_LEN-1-len(str(suffix_counter))], suffix_counter)
            existing_id = picking_binder.to_openerp(bots_id)

        # Select which moves we will ship
        picking_complete = True
        moves_to_split = []
        order_lines = []
        seq = 1

        moves = [move for move in picking.move_lines]
        bundle_sku_count = Counter([move.sale_parent_line_id.product_id.id for move in moves if move.sale_parent_line_id])

        for move in moves:
            if move.state == 'cancel':
                moves_to_split.append(move.id)
                continue
            elif move.state not in ALLOWED_STATES:
                picking_complete = False
                moves_to_split.append(move.id)
                continue
            product_bots_id = move.product_id and product_binder.to_backend(move.product_id.id)
            if not product_bots_id:
                picking_complete = False
                moves_to_split.append(move.id)
                continue

            product_supplier_sku = product_bots_id
            for supplier in move.product_id.seller_ids:
                if supplier.product_code and supplier.name.id == move.partner_id.id:
                    product_supplier_sku = supplier.product_code
                    break

            discount = 0
            price_unit = 0.0
            bundle = False
            currency = default_company.currency_id
            tax_id = []
            if move.sale_line_id:
                price_unit = move.sale_line_id.price_unit

                # Take the parent line's price if no price on simple product
                if move.sale_parent_line_id and not price_unit:
                    sale_order_line = move.sale_parent_line_id
                    price_unit = sale_order_line.price_unit
                    bundle = True
                
                currency = move.sale_line_id.order_id.currency_id
                discount = move.sale_line_id.discount
                tax_id = move.sale_line_id.tax_id
                ordered_qty = move.sale_line_id.product_uom_qty # FIXME: Could also use product_uos_qty - may be worth specifying and converting UoM
            elif move.purchase_line_id:
                price_unit = move.purchase_line_id.price_unit
                currency = move.purchase_line_id.order_id.currency_id
                tax_id = move.purchase_line_id.taxes_id
                ordered_qty = move.purchase_line_id.product_qty
            elif move.picking_id:
                default_currency = currency
                order = False
                if move.picking_id.sale_id and move.picking_id.sale_id.currency_id:
                    currency = move.picking_id.sale_id.currency_id
                    order = move.picking_id.sale_id
                elif move.picking_id.purchase_id and move.picking_id.purchase_id.currency_id:
                    currency = move.picking_id.purchase_id.currency_id
                    order = move.picking_id.purchase_id

                pricelist_price = False
                if order:
                    pricelist_price = _find_pricelist_cost(self.session.cr, self.session.uid, order.pricelist_id.id, move.product_id.id, move.partner_id.id, move.product_uom.id, order.date_order, context=ctx)

                if pricelist_price:
                    # Currency will already be correct since the field on the order
                    # is related to the field on the same pricelist.
                    price_unit = pricelist_price
                elif currency.id != default_currency.id:
                    # Fallback - no price could be found on the pricelist.
                    # Convery standard_price to the correct currency.
                    price_unit = currency_obj.compute(self.session.cr, self.session.uid, default_currency.id, currency.id, price_unit, round=False, context=ctx)
                ordered_qty = move.product_qty

            price_unit = price_unit or move.product_id.list_price
            discounted_price = (1 - (discount / 100.0)) * price_unit

            price = currency_obj.round(self.session.cr, self.session.uid, currency, discounted_price)

            taxes = tax_obj.compute_all(
                self.session.cr, self.session.uid, tax_id, discounted_price, 1,
                move.product_id, move.partner_id
            )

            if bundle:
                # This is to get the correct price for multi-sku bundles where the unit price for each sku has to be
                # total cost of bundle / number of skus
                bundle_count = bundle_sku_count[move.sale_parent_line_id.product_id.id]
                price = (price * 100 // bundle_count) / 100

            price_exc_tax = tax_obj.compute_all(self.session.cr, self.session.uid, tax_id, price_unit * (1-(discount or 0.0)/100.0),
                                            1, move.product_id, move.partner_id)['total'] # Use product quantity of 1 as the unit price is being exported

            precision = dp.get_precision('bots')(self.session.cr)
            precision = precision and precision[1] or 2

            order_line = {
                    "id": "%sS%s" % (bots_id, seq),
                    "seq": seq,
                    "move_id": move.id,
                    "product": product_bots_id,
                    "product_supplier_sku": product_supplier_sku,
                    "product_qty": int(move.product_qty),
                    "ordered_qty": int(ordered_qty),
                    "uom": move.product_uom.name,
                    "product_uos_qty": int(move.product_uos_qty),
                    "uos": move.product_uos.name,
                    "price_unit": round(price, precision),
                    "price_currency": currency.name,
                    "alternative_description": move.name,
                    "bundle": bundle
                }

            if move.product_id.volume:
                order_line['volume_net'] = move.product_id.volume
            if move.product_id.weight:
                order_line['weight'] = move.product_id.weight
            if move.product_id.weight_net:
                order_line['weight_net'] = move.product_id.weight_net
            if move.note:
                order_line['desc'] = move.note and move.note[:64]
            if TYPE == 'in':
                order_line['customs_free_from'] = not picking.bots_customs

            if move.sale_line_id:
                # Maintain backwards compatibility with the bots mapping... but should be removed in the future...
                order_line['price_total_ex_tax'] = round(taxes['total'], precision)
                order_line['price_total_inc_tax'] = round(taxes['total_included'], precision)

                total_rate = 0.0
                tax_rate = 0.0
                for tax in move.sale_line_id.tax_id:
                    if tax.type == 'percent' and tax.price_include == False:
                        total_rate += tax.amount
                    else:
                        break # Only supports aggregating percentage taxes
                        # raise osv.except_osv(_('Error !'), _('This report does not support tax with ID %s') % (tax.id,))
                else:
                    tax_rate = round(total_rate * 100.0, precision)

                order_line['tax_rate'] = tax_rate or (100 * ((taxes['total_included'] - taxes['total']) / taxes['total']))

            order_lines.append(order_line)
            seq += 1

        if not order_lines:
            raise MappingError(_('Unable to export any order lines on export of Bots picking %s.') % (picking_id,))

        # Split picking depending on order policy
        sale_policy = (TYPE == 'out') and picking.sale_id and picking.sale_id.picking_policy or 'direct'
        picking_policy = picking.move_type or sale_policy
        if not picking_complete:
            if TYPE == 'in':
                raise NotImplementedError(_('Exporting a partial incoming picking is not implemented'))
            if picking_policy != 'direct':
                raise InvalidDataError(_('Unable to export picking %s. Picking policy does not allow it to be split and is not fully complete or some products are not mapped for export.') % (picking_id,))
        if moves_to_split:
            # Split the picking
            new_picking_id = picking_obj.copy(self.session.cr, self.session.uid, picking.openerp_id.id,
                                              {
                                                  'move_type': sale_policy,
                                                  'move_lines': [],
                                                  'origin': picking.origin,
                                              },
                                              context=ctx)
            move_obj.write(self.session.cr, self.session.uid, moves_to_split, {'picking_id': new_picking_id}, context=ctx)
            wf_service.trg_validate(self.session.uid, 'stock.picking', new_picking_id, 'button_confirm', self.session.cr)

        partner_data = {
            "id": "P%d" % (picking.partner_id.id),
            "code": picking.partner_id.ref or '',
            "title": picking.partner_id.title and picking.partner_id.title.name or '',
            "jobtitle": picking.partner_id.function or '',
            "company": picking.partner_id.company or '',
            "name": picking.partner_id.name or '',
            "street1": picking.partner_id.street or '',
            "street2": picking.partner_id.street2 or '',
            "city": picking.partner_id.city or '',
            "zip": picking.partner_id.zip or '',
            "country": picking.partner_id.country_id and picking.partner_id.country_id.code or '',
            "state": picking.partner_id.state_id and picking.partner_id.state_id.name or '',
            "phone": picking.partner_id.phone or '',
            "fax": picking.partner_id.fax or '',
            "email": picking.partner_id.email or '',
            "language": picking.partner_id.lang or '',
        }

        billing_data = {}
        if TYPE == 'out' and picking.sale_id and picking.sale_id.partner_invoice_id:
            billing_data = {
                "id": "P%d" % (picking.sale_id.partner_invoice_id.id),
                "code": picking.sale_id.partner_invoice_id.ref or '',
                "title": picking.sale_id.partner_invoice_id.title and picking.sale_id.partner_invoice_id.title.name or '',
                "jobtitle": picking.sale_id.partner_invoice_id.function or '',
                "company": picking.sale_id.partner_invoice_id.company or '',
                "name": picking.sale_id.partner_invoice_id.name or '',
                "street1": picking.sale_id.partner_invoice_id.street or '',
                "street2": picking.sale_id.partner_invoice_id.street2 or '',
                "city": picking.sale_id.partner_invoice_id.city or '',
                "zip": picking.sale_id.partner_invoice_id.zip or '',
                "country": picking.sale_id.partner_invoice_id.country_id and picking.sale_id.partner_invoice_id.country_id.code or '',
                "state": picking.sale_id.partner_invoice_id.state_id and picking.sale_id.partner_invoice_id.state_id.name or '',
                "phone": picking.sale_id.partner_invoice_id.phone or '',
                "fax": picking.sale_id.partner_invoice_id.fax or '',
                "email": picking.sale_id.partner_invoice_id.email or '',
                "language": picking.sale_id.partner_invoice_id.lang or '',
            }

        picking_data = {
                'id': bots_id,
                'name': order_number,
                'order': order_number,
                'state': 'new',
                'type': TYPE,
                'date': datetime.strptime(picking.min_date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y-%m-%d'),
                'ship_date': picking.backend_id.datetime_convert(picking.date_done),
                'partner': partner_data,
                'client_order_ref': TYPE == 'out' and picking.sale_id and picking.sale_id.client_order_ref or '',
                'incoterm': incoterm,
                'tracking_number': picking.carrier_tracking_ref or "",
                'order_date': TYPE == 'out' and picking.sale_id and picking.sale_id.date_order or '',
                'line': order_lines,
            }
        if billing_data:
            picking_data['partner_bill'] = billing_data

        if picking.note:
            picking_data['desc'] = picking.note and picking.note[:64]
        if picking.partner_id.vat:
            picking_data['partner']['vat'] = picking.partner_id.vat

        if self._picking_type == 'out':
            picking_data['prio'] = picking.prio_id.code or '4' # 4 = Use delivery date
        else:
            picking_data['prio'] = '4' # 4 = Use delivery date

        data = {
                'picking': {
                        'pickings': [picking_data,],
                        'header': [{
                                'type': TYPE,
                                'state': 'done',
                                'partner_to': picking.backend_id.name_to,
                                'partner_from': picking.backend_id.name_from,
                                'message_id': '0',
                                'date_msg': picking.backend_id.datetime_convert(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')),
                                'docnum': bots_id,
                            }],
                    },
                }
        return data, FILENAME, bots_id

    def _prepare_delete_data(self, picking_id):
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
        return data, FILENAME

    def create(self, picking_id):
        data, FILENAME, bots_id = self._prepare_create_data(picking_id)
        data = json.dumps(data, indent=4)
        filename_id = self._get_unique_filename(FILENAME)
        self._write(filename_id, data)
        return bots_id

    def delete(self, picking_id):
        data, FILENAME = self._prepare_delete_data(picking_id)
        data = json.dumps(data, indent=4)

        filename_id = self._get_unique_filename(FILENAME)
        self._write(filename_id, data)

@bots
class StockPickingOutAdapter(StockPickingAdapter):
    _model_name = 'bots.stock.picking.out'
    _picking_type = 'out'

@bots
class StockPickingInAdapter(StockPickingAdapter):
    _model_name = 'bots.stock.picking.in'
    _picking_type = 'in'

def picking_available(session, model_name, record_id, picking_type, location_type):
    warehouse_obj = session.pool.get('stock.warehouse')
    bots_warehouse_obj = session.pool.get('bots.warehouse')
    picking = session.browse(model_name, record_id)
    # Check to see if the picking should be exported to the WMS
    # If so create binding, else return
    if not picking.state == 'assigned': # Handle only deliveries which are assigned
        return

    location_ids = []
    if location_type == 'src':
        location = picking.location_id or picking.move_lines and picking.move_lines[0].location_id
        while location and location.id not in location_ids:
            location_ids.append(location.id)
            if location.chained_picking_type != 'in' and location.chained_auto_packing == 'auto':
                location = location.chained_location_id
    else:
        location = picking.location_dest_id or picking.move_lines and picking.move_lines[0].location_dest_id
        while location and location.id not in location_ids:
            location_ids.append(location.id)
            if location.chained_picking_type != 'out' and location.chained_auto_packing == 'auto':
                location = location.chained_location_id

    warehouse_ids = []
    for location_id in location_ids:
        warehouse_ids = warehouse_obj.search(session.cr, session.uid, ['|', ('lot_stock_id', '=', location_id), ('lot_output_id', '=', location_id)])
        if warehouse_ids:
            break

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
    picking_ids = session.search(picking_type, [('openerp_id', '=', record_id)])
    pickings = session.browse(picking_type, picking_ids)

    late_pickings = []

    for picking in pickings:
        min_date = picking.min_date and datetime.strptime(picking.min_date, DEFAULT_SERVER_DATETIME_FORMAT)
        if min_date and not picking.bots_override and datetime.now().date() >= min_date.date() \
                and not all([move.state == 'cancel' for move in picking.move_lines]):
            late_pickings.append(picking.name)
            continue
        if not picking.bots_id:
            picking.unlink()
        elif (picking_type == 'bots.stock.picking.out' and picking.backend_id.feat_picking_out_cancel == 'export') or \
            (picking_type == 'bots.stock.picking.in' and picking.backend_id.feat_picking_in_cancel == 'export'):
            export_picking_cancel.delay(session, picking_type, picking.id)
        else:
            if (picking_type == 'bots.stock.picking.out' and picking.backend_id.feat_picking_out_cancel == 'reject') or \
                (picking_type == 'bots.stock.picking.in' and picking.backend_id.feat_picking_in_cancel == 'reject'):
                raise osv.except_osv(_('Error!'), _('Cancellations are restricted and this picking has already been exported to the warehouse: %s') % (picking.name,))

    if late_pickings:
        raise osv.except_osv(_('Error!'), _('Could not cancel the following pickings, they might have already been delivered by the warehouse: %s') % (", ".join(late_pickings),))

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


@on_record_create(model_names='bots.stock.picking.out')
def delay_export_picking_out(session, model_name, record_id, vals):
    export_picking.delay(session, model_name, record_id)

@on_record_create(model_names='bots.stock.picking.in')
def delay_export_picking_in(session, model_name, record_id, vals):
    export_picking.delay(session, model_name, record_id)

@job
def export_picking(session, model_name, record_id):
    picking_id = session.search(model_name, [('id', '=', record_id)])
    if not picking_id:
        return "Unable to export %s, the mapping record has been deleted" % (record_id,)
    picking = session.browse(model_name, record_id)
    if picking.bots_id:
        return "Unable to export %s, the mapping record has already been exported" % (picking.name,)
    if picking.state == 'done' and session.search(model_name, [('backorder_id', '=', picking.openerp_id.id)]):
        # We are an auto-created back order completed - ignore this export
        return "Not creating backorder for auto-created done picking backorder %s" % (picking.name,)
    if picking.state == 'cancel':
        # We are an auto-created back order completed - ignore this export
        return "Picking %s was cancelled before exported, ignorning." % (picking.name,)
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
