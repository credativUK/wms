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

class SaleOrder(orm.Model):
    _inherit = "sale.order"

    _columns = {
        'requested_delivery_date': fields.date('Requested Delivery Date', select=True, help="Date on which customer has requested delivery.", readonly=True, states={'draft':[('readonly',False)]},),
        'prio_id' : fields.many2one('order.prio', 'Priority', help='The priority code to assign to this order. If blank, will default to \'4\'', readonly=True, states={'draft':[('readonly',False)]}),
    }

    def _get_default_prio(self, cr, uid, context=None):
        pick_obj = self.pool.get('stock.picking')
        return pick_obj._get_default_prio(cr, uid, context=context)

    _defaults = {
        'prio_id' : _get_default_prio,
    }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        vals = super(SaleOrder, self)._prepare_order_picking(cr, uid, order, context=context)
        vals.update({'prio_id' : order.prio_id.id})
        return vals

class SaleOrderLine(orm.Model):
    _inherit = "sale.order.line"

    def _bots_exported_rate(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        picking_obj = self.pool.get('stock.picking')
        bots_picking_out_obj = self.pool.get('bots.stock.picking.out')
        # Get all pickings related to all lines so we are not duplicating reads
        picking_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            for move in line.move_ids:
                if move.picking_id and move.picking_id.type == 'out' and move.picking_id.id not in picking_ids:
                    picking_ids.append(move.picking_id.id)
        # Read if they are exported
        picking_exported_dict = {}
        for picking_id in picking_ids:
            if picking_exported_dict.get(picking_id, False):
                continue
            exported = bots_picking_out_obj.search(cr, uid, [('openerp_id', '=', picking_id), ('bots_id', '!=', False)], context=context) and True or False
            picking_exported_dict[picking_id] = exported
            if not exported:
                # If not exported check for backorders which replace this one
                backorder_ids = picking_obj.search(cr, uid, [('backorder_id' ,'=', picking_id)], context=context)
                if backorder_ids:
                    for backorder_id in backorder_ids:
                        if backorder_id not in picking_ids:
                            picking_ids.append(backorder_id)
            else:
                # If we are exported and we are a backorder, mark the ones we are replacing also as exported
                picking = picking_obj.browse(cr, uid, picking_id, context=context)
                while picking.backorder_id:
                    picking_exported_dict[picking.backorder_id.id] = True
                    picking = picking.backorder_id

        # From the cached exported data, calculate the rates
        for line in self.browse(cr, uid, ids, context=context):
            moves_exported, moves_total = 0, 0
            for move in line.move_ids:
                if move.state == 'cancel':
                    continue
                moves_total += move.product_qty
                if move.picking_id and picking_exported_dict.get(move.picking_id.id, False):
                    moves_exported += move.product_qty
            res[line.id] = "%d / %d" % (moves_exported, moves_total)
        return res

    _columns = {
        'requested_delivery_date': fields.date('Requested Delivery Date', select=True, help="Date on which customer has requested delivery.", readonly=True, states={'draft':[('readonly',False)]},),
        'bots_exported_rate': fields.function(_bots_exported_rate, type='char', string='Exported to 3PL', readonly=True, help="Quantity of products which have been exported to 3PL/Bots"),
    }
