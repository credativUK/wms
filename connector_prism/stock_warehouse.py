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

from openerp import sql_db
from openerp.addons.connector.queue.job import job
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta

from openerp.addons.connector_bots.backend import bots
from openerp.addons.connector_bots.stock_warehouse import WarehouseAdapter
from openerp.addons.connector.exception import RetryableJobError

import logging
_logger = logging.getLogger(__name__)

@bots(replacing=WarehouseAdapter)
class PrismWarehouseAdapter(WarehouseAdapter):
    _model_name = 'bots.warehouse'

    def _handle_confirmations(self, cr, uid, stock_picking, prod_confirm, context=None):
        if stock_picking.type == 'in' and stock_picking.purchase_id:
            purchase = stock_picking.purchase_id
            purchase_obj = self.session.pool.get('purchase.order')
            read_fields = ['bots_cross_dock', 'bots_cut_off']
            purchase_data = purchase_obj.read(cr, uid, purchase.id, read_fields, context=context)
            if purchase_data['bots_cross_dock'] and not purchase_data['bots_cut_off']:
                bots_wh_obj = self.session.pool.get('bots.warehouse')
                wh_id = purchase.warehouse_id.id
                bots_wh_ids = bots_wh_obj.search(cr, uid, [('warehouse_id', '=', wh_id)], context=context)
                if bots_wh_ids:
                    _cr = sql_db.db_connect(cr.dbname).cursor()
                    self.session.cr = _cr
                    purchase_cutoff.delay(self.session, 'bots.warehouse', bots_wh_ids[0], [purchase.id], priority=10)
                    _cr.commit()
                    _cr.close()
                    self.session.cr = cr
                    raise RetryableJobError(
                            'Picking %s can be confirmed only once Purchase Order %s has been cut off. '
                            'This has now been scheduled; the job will be retried later.' %
                            (stock_picking.name, purchase.name)
                    )

        return super(PrismWarehouseAdapter, self)._handle_confirmations(cr, uid, stock_picking, prod_confirm, context=context)

class BotsStockWarehouse(orm.Model):
    _inherit = 'bots.warehouse'

    def purchase_cutoff(self, cr, uid, ids, all_purchase_ids, context=None):
        '''Find purchases with cut-off passed and export'''

        purchase_obj = self.pool.get('purchase.order')
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        purchase_line_obj = self.pool.get('purchase.order.line')
        procurement_obj = self.pool.get('procurement.order')
        backend_obj = self.pool.get('bots.backend')

        for warehouse in self.browse(cr, uid, ids, context=context):
            purchase_ids = purchase_obj.search(cr, uid, [('warehouse_id', '=', warehouse.warehouse_id.id),
                                                         ('id', 'in', all_purchase_ids),
                                                         ('bots_cut_off', '=', False)], context=context)
            # Find all linked moves for all purchases
            moves = []
            for purchase in purchase_obj.browse(cr, uid, purchase_ids, context=context):
                moves.extend([l.move_dest_id for l in purchase.order_line if l.move_dest_id])
            # Group moves by picking
            picking_dict = {}
            for move in moves:
                picking_dict.setdefault(move.picking_id.id, []).append(move.id)

            force_move_ids = []
            deallocate_move_ids = []

            for picking_id, move_ids in picking_dict.iteritems():
                # Find all other confirmed moves in this picking
                other_move_ids = move_obj.search(cr, uid, [('picking_id', '=', picking_id), ('id', 'not in', move_ids), ('state', 'not in' ,('done', 'assigned', 'cancel'))], context=context)

                l_force_move_ids = []
                l_deallocate_move_ids = []
                skip = False

                picking = picking_obj.browse(cr, uid, picking_id, context=context)
                for move_id in other_move_ids:
                    # If confirmed move in another cut-off PO we should make it available
                    pol_id = purchase_line_obj.search(cr, uid, [('move_dest_id', '=', move_id), ('order_id.bots_cut_off', '=', True), ('state', 'not in', ('draft', 'cancel'))], context=context)
                    if pol_id:
                        l_force_move_ids.append(move_id)
                        continue

                    # If confirmed move in another PO pending cut-off we should leave it as is (it will be assigned once this PO is cut-off)
                    cutoff = backend_obj._get_cutoff_date(cr, uid, [warehouse.backend_id.id], context=context)
                    pol_id = purchase_line_obj.search(cr, uid, [('move_dest_id', '=', move_id),
                                                                ('order_id.warehouse_id', '=', warehouse.warehouse_id.id),
                                                                ('order_id.bots_cross_dock', '=', True),
                                                                ('order_id.minimum_planned_date', '<=', cutoff),
                                                                ('order_id.state', '=', 'approved'),
                                                                ('order_id.bots_cut_off', '=', False)], context=context)
                    if pol_id:
                        skip = True
                        break

                    # We have a move linked to a non-cut off PO or to nothing and we are all at once, Deallocate.
                    if picking.move_type == 'one':
                        l_deallocate_move_ids.extend(move_ids)
                        break

                else:
                    # We are not skipping or deallocating - allocate the moves
                    l_force_move_ids.extend(move_ids)

                if skip:
                    continue
                force_move_ids.extend(l_force_move_ids)
                deallocate_move_ids.extend(l_deallocate_move_ids)

            if deallocate_move_ids:
                # We cannot split the delivery because there are moves which cannot be completed
                procurement_ids = procurement_obj.search(cr, uid, [('move_id', 'in', deallocate_move_ids)], context=context)
                #procurement_obj.write(cr, uid, procurement_ids, {'purchase_id': False}, context=context)
                _logger.debug('Procurements are deliver at once. cannot be cross-docked: %s' % (procurement_ids,))
                move_obj.force_assign(cr, uid, deallocate_move_ids, context=context)

            force_move_ids = move_obj.search(
                cr, uid, [('id', 'in', force_move_ids), ('state', 'in', ('confirmed','waiting'))], context=context
            )

            if force_move_ids:
                # We are either complete or are able to split the order, assign everything that doesn't need splitting
                move_obj.force_assign(cr, uid, force_move_ids, context=context)

            purchase_obj.write(cr, uid, purchase_ids, {'bots_cut_off': True}, context=context)

        return True

@job
def purchase_cutoff(session, model_name, record_id, purchase_ids, new_cr=True):
    warehouse = session.browse(model_name, record_id)
    return warehouse.purchase_cutoff(purchase_ids)
