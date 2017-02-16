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

from openerp.osv import orm, fields, osv

from openerp.addons.connector.session import ConnectorSession
from .event import on_picking_out_done, on_picking_out_available, on_picking_in_available, on_picking_out_cancel, on_picking_in_cancel

class stock_picking(orm.Model):
    _inherit = 'stock.picking'

    _columns = {
        'wms_disable_events': fields.boolean('Disable WMS Events', help='Prevent events from fireing to allow overriding the workflow'),
    }

    _defaults = {
        'wms_disable_events': False,
    }

    def action_assign_wkf(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_assign_wkf(cr, uid, ids, context=context)
        if res:
            session = ConnectorSession(cr, uid, context=context)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type', 'wms_disable_events'],
                                    context=context)
            for picking_vals in picking_records:
                if picking_vals['wms_disable_events']:
                    continue
                if picking_vals['type'] == 'out':
                    on_picking_out_available.fire(session, self._name, picking_vals['id'])
                elif picking_vals['type'] == 'in':
                    on_picking_in_available.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res


    def action_assign(self, cr, uid, ids, *args, **kwargs):
        res = super(stock_picking, self).action_assign(cr, uid, ids, *args, **kwargs)
        if res:
            session = ConnectorSession(cr, uid, context=None)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type', 'wms_disable_events'],
                                    context=None)
            for picking_vals in picking_records:
                if picking_vals['wms_disable_events']:
                    continue
                if picking_vals['type'] == 'out':
                    on_picking_out_available.fire(session, self._name, picking_vals['id'])
                elif picking_vals['type'] == 'in':
                    on_picking_in_available.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res

    def action_cancel(self, cr, uid, ids, *args, **kwargs):
        context = kwargs.get('context', {})
        # If the state of the picking is already cancelled we should not export it again
        cancel_ids = []
        for picking_vals in self.read(cr, uid, ids, ['id', 'state', 'wms_disable_events'], context=context):
            if picking_vals['wms_disable_events']:
                continue
            if picking_vals['state'] != 'cancel':
                cancel_ids.append(picking_vals['id'])
        res = super(stock_picking, self).action_cancel(cr, uid, ids, *args, **kwargs)
        # New cancellations should be exported
        if cancel_ids:
            session = ConnectorSession(cr, uid, context=context)
            picking_records = self.read(cr, uid, cancel_ids,
                                    ['id', 'type'],
                                    context=context)
            for picking_vals in picking_records:
                if picking_vals['type'] == 'out':
                    on_picking_out_cancel.fire(session, self._name, picking_vals['id'])
                elif picking_vals['type'] == 'in':
                    on_picking_in_cancel.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res

    def action_confirm(self, cr, uid, ids, context=None):
        # If the state of the picking was assigned we should cancel the export
        assigned_ids = []
        for picking_vals in self.read(cr, uid, ids, ['id', 'state', 'wms_disable_events'], context=context):
            if picking_vals['wms_disable_events']:
                continue
            if picking_vals['state'] == 'assigned':
                assigned_ids.append(picking_vals['id'])
        res = super(stock_picking, self).action_confirm(cr, uid, ids, context=context)
        # Assigned pickings should be cancelled by the connector
        if assigned_ids:
            session = ConnectorSession(cr, uid, context=context)
            picking_records = self.read(cr, uid, assigned_ids,
                                    ['id', 'type'],
                                    context=context)
            for picking_vals in picking_records:
                if picking_vals['type'] == 'out':
                    on_picking_out_cancel.fire(session, self._name, picking_vals['id'])
                elif picking_vals['type'] == 'in':
                    on_picking_in_cancel.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res

    def action_done(self, cr, uid, ids, *args, **kwargs):
        res = super(stock_picking, self).action_done(cr, uid, ids, *args, **kwargs)
        if res:
            session = ConnectorSession(cr, uid, context=None)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type', 'wms_disable_events'],
                                    context=None)
            for picking_vals in picking_records:
                if picking_vals['wms_disable_events']:
                    continue
                if picking_vals['type'] == 'out':
                    on_picking_out_done.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res
