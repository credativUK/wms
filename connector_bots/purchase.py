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

class PurchaseOrder(orm.Model):
    _inherit = 'purchase.order'

    _columns = {
            'bots_customs': fields.boolean('Bonded Goods', help='If this picking is subject to duties. (DSV only)', states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}),
        }

    _defaults = {
            'bots_customs':  lambda *a: False,
        }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = super(PurchaseOrder, self)._prepare_order_picking(cr, uid, order, context=context)
        res['bots_customs'] = order.bots_customs
        return res

    def _fixup_created_picking(self, cr, uid, ids, line_moves, remain_moves, context=None):
        bots_stock_picking_in_obj = self.pool.get('bots.stock.picking.in')
        res = super(PurchaseOrder, self)._fixup_created_picking(cr, uid, ids, line_moves, remain_moves, context)
        for purchase in self.browse(cr, uid, ids, context=context):
            # Take bots records from purchase.order_edit_id.picking_ids and move to purchase.order_edit_id sicne we do not support editing POs in PRISM
            if not purchase.order_edit_id or not purchase.order_edit_id.picking_ids or not purchase.picking_ids:
                continue
            bots_stock_picking_in_ids = bots_stock_picking_in_obj.search(cr, uid, [('openerp_id', 'in', [x.id for x in purchase.order_edit_id.picking_ids])], context=context)
            if len(bots_stock_picking_in_ids) > 1:
                raise NotImplementedError('Purchase order is exported mutliple times and cannot be edited.')
            if bots_stock_picking_in_ids:
                extra_bots_stock_picking_in_ids = bots_stock_picking_in_obj.search(cr, uid, [('openerp_id', 'in', [x.id for x in purchase.picking_ids])], context=context)
                bots_stock_picking_in_obj.unlink(cr, uid, extra_bots_stock_picking_in_ids, context=context)
                bots_stock_picking_in_obj.write(cr, uid, bots_stock_picking_in_ids, {'openerp_id': purchase.picking_ids[0].id}, context=context)
        return res
