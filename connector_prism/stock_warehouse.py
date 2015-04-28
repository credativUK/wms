# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 credativ Ltd
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
from openerp import pooler, netsvc, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.connector.queue.job import job
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta

class BotsStockWarehouse(orm.Model):
    _inherit = 'bots.warehouse'

    def purchase_cutoff(self, cr, uid, ids, context=None):
        '''Find purchases with cut-off passed and export'''

        purchase_obj = self.pool.get('purchase.order')
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        purchase_line_obj = self.pool.get('purchase.order.line')
        procurement_obj = self.pool.get('procurement.order')

        for warehouse in self.browse(cr, uid, ids, context=context):
            # Find all POs passed their cut off
            cutoff = (datetime.now() + timedelta(days=warehouse.backend_id.crossdock_cutoff_days)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            purchase_ids = purchase_obj.search(cr, uid, [('warehouse_id', '=', warehouse.warehouse_id.id),
                                                         ('bots_cross_dock', '=', True),
                                                         ('minimum_planned_date', '<=', cutoff),
                                                         ('state', '=', 'approved'),
                                                         ('bots_cut_off', '=', False)], context=context)
            # Find all linked moves for all purchases
            for purchase in purchase_obj.browse(cr, uid, purchase_ids, context=context):
                moves = [l.move_dest_id for l in purchase.order_line if l.move_dest_id]
            # Group moves by picking
            picking_dict = {}
            for move in moves:
                picking_dict.setdefault(move.picking_id.id, []).append(move.id)

            for picking_id, move_ids in picking_dict.iteritems():
                other_move_ids = move_obj.search(cr, uid, [('picking_id', '=', picking_id), ('id', 'not in', move_ids), ('state', 'not in' ,('done', 'assigned', 'cancel'))], context=context)
                split_move_ids = []
                force_move_ids = []

                picking = picking_obj.browse(cr, uid, picking_id, context=context)
                for move_id in other_move_ids:
                    # If confirmed move in another cut-off PO we should make it available
                    pol_id = purchase_line_obj.search(cr, uid, [('move_dest_id', '=', move_id), ('bots_cut_off', '=', True), ('state', 'not in', ('draft', 'cancel'))], context=context)
                    if pol_id:
                        force_move_ids.append(move_id)
                        continue

                    # If confirmed move related to another PO we should split it 
                    pol_id = purchase_line_obj.search(cr, uid, [('move_dest_id', '=', move_id), ('state', 'not in', ('draft', 'cancel'))], context=context)
                    if pol_id:
                        split_move_ids.append(move_id)
                        continue

                    # Else see if we can assign the move
                    cr.execute('SAVEPOINT crossdock')
                    assign_res = move_obj.action_assign(cr, uid, [move_id], context=context)
                    if assign_res == 1:
                        force_move_ids.append(move_id)
                    else:
                        split_move_ids.append(move_id)
                    cr.execute('ROLLBACK TO SAVEPOINT crossdock')
                    cr.execute('RELEASE SAVEPOINT crossdock')

                if split_move_ids and picking.move_type == 'one':
                    # We cannot split the delivery and there are moves which cannot be completed, remove moves from their purchases
                    procurement_ids = procurement_obj.search(cr, uid, [('move_id', 'in', move_ids)], context=context)
                    procurement_obj.write(cr, uid, procurement_ids, {'purchase_id': False}, context=context)
                else:
                    # We are either complete or are able to split the order, assign everything that doesn't need splitting
                    move_obj.force_assign(cr, uid, move_ids + force_move_ids, context=context)

            purchase_obj.write(cr, uid, purchase_ids, {'bots_cut_off': True}, context=context)

        return True

@job
def purchase_cutoff(session, model_name, record_id, new_cr=True):
    warehouse = session.browse(model_name, record_id)
    return warehouse.purchase_cutoff()
