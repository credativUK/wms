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
        }

    _defaults = {
            'bots_cross_dock':  lambda *a: False,
        }

    def allocate_check_restrict(self, cr, uid, ids, context=None):
        restricted_ids = super(PurchaseOrder, self).allocate_check_restrict(cr, uid, ids, context=context)
        bots_picking_obj = self.pool.get('bots.stock.picking.in')
        for purchase in self.browse(cr, uid, ids, context=context):
            if purchase.bots_cross_dock:
                # Check if now + cutoff time >= arrival time
                bots_picking_ids = bots_picking_obj.search(cr, uid, [('purchase_id', '=', purchase.id),], context=context)
                for bots_picking in bots_picking_obj.browse(cr, uid, bots_picking_ids, context=context):
                    delay = datetime.strptime(bots_picking.minimum_planned_date, DEFAULT_SERVER_DATE_FORMAT) - datetime.now()
                    if bots_picking.backend_id.feat_picking_out_crossdock and delay <= timedelta(days=bots_picking.backend_id.crossdock_cutoff_days):
                        restricted_ids.append(purchase.id)
                        break
        return list(set(restricted_ids))

    def bots_test_exported(self, cr, uid, ids, doraise=False, cancel=False, context=None):
        context = context or {}
        if context.get('wms_bots', False):
            return False
        exported = self.pool.get('bots.stock.picking.in').search(cr, SUPERUSER_ID, [('openerp_id', 'in', ids), ('move_lines.state', 'not in', ('done', 'cancel')), ('bots_override', '=', False)], context=context)
        if exported and cancel:
            exported_obj = self.pool.get('bots.stock.picking.in').browse(cr, uid, exported, context=context)
            exported = [x.id for x in exported_obj if not x.bots_id or not x.backend_id.feat_picking_in_cancel]
        if exported and doraise:
            raise osv.except_osv(_('Error!'), _('This picking has been exported to an external WMS and cannot be modified directly in OpenERP.'))
        return exported or False


        return list(set(restricted_ids))
