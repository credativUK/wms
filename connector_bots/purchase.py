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
            'bots_cross_dock': fields.boolean('Cross Dock', help='Should this order be cross-docked in the warehouse. (Prism only).', states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}),
        }

    _defaults = {
            'bots_customs':  lambda *a: False,
            'bots_cross_dock':  lambda *a: False,
        }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = super(PurchaseOrder, self)._prepare_order_picking(cr, uid, order, context=context)
        res['bots_customs'] = order.bots_customs
        return res
