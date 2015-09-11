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

    _columns = {
        'requested_delivery_date': fields.date('Requested Delivery Date', select=True, help="Date on which customer has requested delivery.", readonly=True, states={'draft':[('readonly',False)]},),
    }
