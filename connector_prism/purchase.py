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
from datetime import datetime, timedelta
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT

class PurchaseOrder(orm.Model):
    _inherit = 'purchase.order'

    _columns = {
            'bots_cross_dock': fields.boolean('Cross Dock', help='Should this order be cross-docked in the warehouse. (Prism only).', states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}),
            'bots_cut_off': fields.boolean('Purchase Cut Off', help='Purchase Order has been cut off and can no longer be modified (Prism only).', readonly=True),
        }

    _defaults = {
            'bots_cross_dock':  lambda *a: False,
            'bots_cut_off':  lambda *a: False,
        }

    def allocate_check_restrict(self, cr, uid, ids, context=None):
        restricted_ids = super(PurchaseOrder, self).allocate_check_restrict(cr, uid, ids, context=context)
        bots_picking_obj = self.pool.get('bots.stock.picking.in')
        for purchase in self.browse(cr, uid, ids, context=context):
            all_picking_ids = bots_picking_obj.search(cr, uid, [('purchase_id', '=', purchase.id)], context=context)
            override_picking_ids = bots_picking_obj.search(cr, uid, [('purchase_id', '=', purchase.id), ('bots_override', '=', True)], context=context)
            if override_picking_ids or not all_picking_ids:
                continue
            elif purchase.bots_cross_dock and purchase.bots_cut_off:
                restricted_ids.append(purchase.id)
        return list(set(restricted_ids))
