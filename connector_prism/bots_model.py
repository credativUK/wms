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

from openerp.osv import fields, orm
from .stock_warehouse import purchase_cutoff
from openerp.addons.connector.session import ConnectorSession
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta

class BotsBackend(orm.Model):
    _inherit = 'bots.backend'

    _columns = {
        'feat_picking_out_crossdock': fields.boolean('Export Cross-Dock Allocations', help='Export cross-dock join files for outgoing moves and their related purchase order pickings'),
        'crossdock_cutoff_days': fields.float('WMS Cut-off days', help='Number of days before a purchase order is cut-off to allow cross-dock details to be exported to the WMS. After this point it will not be possible to edit a PO or any related SOs.'),
    }

    _defaults = {
        'feat_picking_out_crossdock': False,
        'crossdock_cutoff_days': 1.0,
    }

    def _scheduler_purchase_cutoff(self, cr, uid, domain=None, context=None):
        self._bots_backend(cr, uid, self.purchase_cutoff, domain=domain, context=context)

    def _get_cutoff_date(self, cr, uid, ids, context=None):
        for backend in self.browse(cr, uid, ids, context=context):
            cutoff = (datetime.now() + timedelta(days=backend.crossdock_cutoff_days)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            return cutoff
        return datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

    def purchase_cutoff(self, cr, uid, ids, context=None):
        """  Process purchase order cut-offs from all warehouses """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        warehouse_obj = self.pool.get('bots.warehouse')
        purchase_obj = self.pool.get('purchase.order')
        warehouse_ids = warehouse_obj.search(cr, uid, [('backend_id', 'in', ids)], context=context)
        warehouses = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
        for warehouse in warehouses:
            if warehouse.backend_id.feat_picking_out_crossdock:
                # Find all POs passed their cut off
                cutoff = self._get_cutoff_date(cr, uid, [warehouse.backend_id.id], context=context)
                purchase_ids = purchase_obj.search(cr, uid, [('warehouse_id', '=', warehouse.warehouse_id.id),
                                                         ('bots_cross_dock', '=', True),
                                                         ('minimum_planned_date', '<=', cutoff),
                                                         ('state', '=', 'approved'),
                                                         ('bots_cut_off', '=', False)], context=context)
                if purchase_ids:
                    session = ConnectorSession(cr, uid, context=context)
                    for purchase_id in purchase_ids:
                        purchase_cutoff.delay(session, 'bots.warehouse', warehouse.id, [purchase_id], priority=10)
        return True
