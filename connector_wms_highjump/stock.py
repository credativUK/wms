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

import logging
from openerp.osv import orm, fields
from .unit.binder import HighJumpBinder
from .backend import highjump
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_create
from openerp.addons.connector_wms.event import on_picking_out_available
from openerp.addons.connector.exception import MappingError, InvalidDataError
from openerp.addons.connector.unit.synchronizer import (ImportSynchronizer,
                                                        ExportSynchronizer
                                                        )
from openerp import netsvc
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

from datetime import datetime

_logger = logging.getLogger(__name__)

class stock_picking(orm.Model):
    _inherit = 'stock.picking.out'

    def highjump_test_exported(self, cr, uid, ids, doraise=False, context=None):
        exported = self.pool.get('highjump.stock.picking.out').search(cr, SUPERUSER_ID, [('openerp_id', 'in', ids)], context=context)
        if exported and doraise:
            raise osv.except_osv(_('Error!'), _('This picking has been exported to an external WMS and cannot be modified directly in OpenERP.'))
        return exported or False

    def cancel_assign(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).cancel_assign(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_cancel(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def action_done(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_done(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).unlink(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def hj_import_picking_tracking(self, cr, uid, ids, context=None):
        # Create a deferred job to import tracking details for this picking
        binding_ids = self.pool.get('highjump.stock.picking.out').search(cr, uid, [('openerp_id', 'in', ids)])
        for binding_id in binding_ids:
            import_picking_tracking.delay(session, 'highjump.stock.picking.out', binding_id, priority=1)
        return True

class stock_move(orm.Model):
    _inherit = 'stock.move'

    def highjump_test_exported(self, cr, uid, ids, doraise=False, context=None):
        picking_ids = [x['picking_id'] and x['picking_id'][0] for x in self.read(cr, uid, ids, ['picking_id',], context=context)]
        if picking_ids:
            exported = self.pool.get('stock.picking.out').highjump_test_exported(cr, uid, ids, doraise=doraise, context=context)
            return exported
        return False

    def cancel_assign(self, cr, uid, ids, context=None):
        res = super(stock_move, self).cancel_assign(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        res = super(stock_move, self).action_cancel(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def action_done(self, cr, uid, ids, context=None):
        res = super(stock_move, self).action_done(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def action_scrap(self, cr, uid, ids, context=None):
        res = super(stock_move, self).action_scrap(cr, uid, ids, context=context)
        self.highjump_test_exported(cr, uid, ids, doraise=True, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(stock_move, self).unlink(cr, uid, ids, context=context)
        self._test_exported(cr, uid, ids, doraise=True, context=context)
        return res

class highjump_stock_picking_out_tracking(orm.TransientModel):
    _name = 'highjump.stock.picking.out.tracking'
    _description = "High Jump Download Stock Picking Tracking"

    def download_tracking(self, cr, uid, ids, context=None):
        picking_ids = context.get('active_ids', [])
        self.pool.get('stock.picking').hj_import_picking_tracking(cr, uid, picking_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

class highjump_stock_picking(orm.Model):
    _name = 'highjump.stock.picking.out'
    _inherit = 'highjump.binding'
    _inherits = {'stock.picking.out': 'openerp_id'}
    _description = 'High Jump Stock Picking'

    _columns = {
        'openerp_id': fields.many2one('stock.picking.out',
                                      string='Stock Picking',
                                      required=True,
                                      ondelete='restrict'),
        }

@highjump
class HighJumpStockPickingBinder(HighJumpBinder):
    _model_name = [
            'highjump.stock.picking.out',
        ]

@highjump
class StockPickingAdapter(HighJumpCRUDAdapter):
    _model_name = 'highjump.stock.picking.out'

    def create(self, picking_id):
        product_binder = self.get_binder_for_model('highjump.product.product')
        picking_obj = self.session.pool.get('stock.picking')
        wf_service = netsvc.LocalService("workflow")

        picking = picking_obj.browse(self.session.cr, self.session.uid, picking_id, context=self.session.context)
        order_number = picking.sale_id and picking.sale_id.name or picking.name
        address = picking.partner_id or picking.sale_id and picking.sale_id.partner_shipping_id

        if not address:
            raise MappingError(_('Missing address when attempting to export picking %s.') % (picking_id,))

        # Select which moves we will ship
        picking_complete = True
        moves_to_ship = {}
        order_lines = []
        for move in picking.move_lines:
            if move.state != 'assigned':
                picking_complete = False
                continue
            product_hjid = move.product_id and product_binder.to_highjump(move.product_id.id)
            if not product_hjid:
                picking_complete = False
                continue
            moves_to_ship['move%s' % (move.id)] = {
                    'product_id': move.product_id.id,
                    'product_qty': move.product_qty,
                    'product_uom': move.product_uom.id,
                    'prodlot_id': move.prodlot_id.id,
                }
            order_lines.append({
                    'OrderSKU': product_hjid,
                    'Quantity': move.product_qty,
                })

        # Split picking depending on order policy
        if not picking_complete:
            picking_policy = picking.sale_id and picking.sale_id.picking_policy or 'direct'
            if picking_policy != 'direct':
                raise InvalidDataError(_('Unable to export picking %s. Picking policy does not allow it to be split and is not fully complete or some products are not mapped for export.') % (picking_id,))
            # Split the picking
            split = picking_obj.do_partial(self.session.cr, self.session.uid, [picking_id], moves_to_ship, context=self.session.context)
            picking = split[picking_id].get('delivered_picking', picking)
        else:
            wf_service.trg_validate(self.session.uid, 'stock.picking', picking_id, 'button_done', self.session.cr)

        highjump_id = '%s%s' % (self.highjump.hj_order_prefix, order_number,),
        data = {
                'orderRequest': {
                        'ClientCode': self.highjump.username,
                        'OrderNumber': highjump_id,
                        'PO': highjump_id,
                        'Shipper': self.highjump.hj_shipper,
                        'ShipDate': datetime.now().strftime('%Y-%m-%d'),
                        'DeliveryDate': datetime.now().strftime('%Y-%m-%d'),
                        'Priority': self.highjump.hj_priority,
                        'ServiceLevel': self.highjump.hj_service_level,
                        'DeliveryInstructions': picking.note or picking.sale_id and picking.sale_id.note or '',
                        'Consignee': {
                                'Name': address.name or '',
                                'Address': address.street or '',
                                'Address2': address.street2 or '',
                                'City': address.city or '',
                                'State': address.state_id and address.state_id.code or '',
                                'Zip': address.zip or '',
                                'Country': address.country_id and address.country_id.code or '',
                                'Phone': address.phone or '',
                            }
                        'SKUs': order_lines,
                    },
                }
        res = self._call('PlaceOrder', data)
        raise NotImplementedError  # TODO: process results for errors
        return highjump_id

    def get_tracking(self, binding_id):
        picking = self.session.browse(self.model._name, binding_id)
        data = {
                'orderStatusRequest': {
                        'ClientCode': self.highjump.username,
                        'OrderNumber': picking.highjump_id,
                    },
                }
        res = self._call('OrderStatus', data)
        tracking = None
        raise NotImplementedError # TODO: process results for tracking and errors
        return tracking

@highjump
class HighJumpPickingExport(ExportSynchronizer):
    _model_name = ['highjump.stock.picking.out']

    def run(self, binding_id):
        """
        Export the picking to HighJump
        """
        try:
            highjump_id = self.backend_adapter.create(binding_id)
        except Exception, e: # TODO: process specific errors
            raise
        else:
            self.binder.bind(highjump_id, binding_id)

@highjump
class HighJumpPickingImport(ImportSynchronizer):
    _model_name = ['highjump.stock.picking.out']

    def run(self, binding_id):
        """
        Export the picking to HighJump
        """
        try:
            tracking = self.backend_adapter.get_tracking(binding_id)
        except Exception, e: # TODO: process specific errors
            raise
        else:
            if tracking:
                picking = self.session.write(self.model._name, binding_id, {'carrier_tracking_ref': tracking})

@on_picking_out_available
def picking_out_available(session, model_name, record_id):
    warehouse_obj = session.pool.get('stock.warehouse')
    hj_warehouse_obj = session.pool.get('highjump.warehouse')
    # Check to see if the picking should be exported to the WMS
    # If so create binding, else return
    picking = session.browse(model_name, record_id)
    if not picking.sale_id: # Handle only deliveries from SO, no manual moves
        return
    warehouse_ids = warehouse_obj.search(session.cr, session.uid, [('lot_stock_id', '=', picking.location_id)])
    hj_warehouse_ids = hj_warehouse_obj.search(session.cr, session.uid, [('warehouse_id', 'in', warehouse_ids)])
    hj_warehouse = hj_warehouse_obj.read(session.cr, session.uid, hj_warehouse_ids, ['backend_id'])
    backend_ids = set([x['backend_id'][0] for x in hj_warehouse if x.get('backend_id')])
    for backend_id in backend_ids:
        session.create('highjump.stock.picking.out',
                       {'backend_id': backend_id,
                        'openerp_id': picking.id)

@on_record_create(model_names='highjump.stock.picking.out')
def delay_export_picking_available(session, model_name, record_id, vals):
    export_picking_done.delay(session, model_name, record_id)

@job
def export_picking_available(session, model_name, record_id):
    picking = session.browse(model_name, record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(HighJumpPickingExport)
    res = picking_exporter.run(record_id)
    import_picking_tracking.delay(session, 'highjump.stock.picking.out', record_id, eta=60*60) # Delay tracking import by 1 hour
    return res

@job
def import_picking_tracking(session, model_name, record_id):
    picking = session.browse(model_name, record_id)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_importer = env.get_connector_unit(HighJumpPickingImport)
    res = picking_importer.run(record_id)
    return res
