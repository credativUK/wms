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

class ProcurementOrder(orm.Model):
    _inherit = 'procurement.order'

    def action_mto_to_mts(self, cr, uid, ids, context=None):
        # If the PO has overrides enabled we should allow procurements to be removed from the PO but remain available
        bots_picking_obj = self.pool.get('bots.stock.picking.in')
        order_skip, order_no_skip, procurement_cancel = [], [], []
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.purchase_id.id in order_no_skip:
                procurement_cancel.append(procurement.id)
            elif procurement.purchase_id.id in order_skip:
                continue
            else:
                all_picking_ids = bots_picking_obj.search(cr, uid, [('purchase_id', '=', procurement.purchase_id.id)], context=context)
                override_picking_ids = bots_picking_obj.search(cr, uid, [('purchase_id', '=', procurement.purchase_id.id), ('bots_override', '=', True)], context=context)
                if override_picking_ids or not all_picking_ids:
                    order_skip.append(procurement.purchase_id.id)
                else:
                    order_no_skip.append(procurement.purchase_id.id)
                    procurement_cancel.append(procurement.id)

        self.write(cr, uid, ids, {'state': 'exception', 'procure_method': 'make_to_stock', 'message': False}, context=context)
        if procurement_cancel:
            self._cancel_stock_assign(cr, uid, procurement_cancel, context=context)
        self._cancel_po_assign(cr, uid, ids, context=context)
        return True
