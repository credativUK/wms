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

class BotsBackend(orm.Model):
    _inherit = 'bots.backend'

    _columns = {
        'feat_picking_out_crossdock': fields.boolean('Export Cross-Dock Allocations', help='Export cross-dock join files for outgoing moves and their related purchase order pickings'),
    }

    _defaults = {
        'feat_picking_out_crossdock': False,
    }

    def _scheduler_purchase_cutoff(self, cr, uid, domain=None, context=None):
        self._bots_backend(cr, uid, self.purchase_cutoff, domain=domain, context=context)

    def purchase_cutoff(self, cr, uid, ids, context=None):
        """  Process purchase order cut-offs from all warehouses """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        warehouse_obj = self.pool.get('bots.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [('backend_id', 'in', ids)], context=context)
        warehouses = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
        for warehouse in warehouses:
            if warehouse.backend_id.feat_picking_out_crossdock:
                session = ConnectorSession(cr, uid, context=context)
                purchase_cutoff.delay(session, 'bots.warehouse', warehouse.id)
        return True
