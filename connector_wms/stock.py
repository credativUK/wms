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

from openerp.osv import orm,osv

from openerp.addons.connector.session import ConnectorSession
from .event import on_picking_out_done, on_picking_out_available, on_picking_in_available

class stock_picking(orm.Model):
    _inherit = 'stock.picking'

    def action_assign_wkf(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_assign_wkf(cr, uid, ids, context=context)
        if res:
            session = ConnectorSession(cr, uid, context=context)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type'],
                                    context=context)
            for picking_vals in picking_records:
                if picking_vals['type'] == 'out':
                    on_picking_out_available.fire(session, self._name, picking_vals['id'])
                elif picking_vals['type'] == 'in':
                    on_picking_in_available.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res


    def action_assign(self, cr, uid, ids, *args):
        res = super(stock_picking, self).action_assign(cr, uid, ids, *args)
        if res:
            session = ConnectorSession(cr, uid, context=None)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type'],
                                    context=None)
            for picking_vals in picking_records:
                if picking_vals['type'] == 'out':
                    on_picking_out_available.fire(session, self._name, picking_vals['id'])
                elif picking_vals['type'] == 'in':
                    on_picking_in_available.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res

    def action_done(self, cr, uid, ids, *args):
        res = super(stock_picking, self).action_done(cr, uid, ids, *args)
        if res:
            session = ConnectorSession(cr, uid, context=None)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type'],
                                    context=None)
            for picking_vals in picking_records:
                if picking_vals['type'] == 'out':
                    on_picking_out_done.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res
