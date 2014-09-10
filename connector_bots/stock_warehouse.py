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
from openerp import pooler, netsvc, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import JobError, NoExternalId
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer

from .unit.binder import BotsModelBinder
from .unit.backend_adapter import BotsCRUDAdapter, file_to_process
from .backend import bots
from .connector import get_environment, add_checkpoint

import json
import traceback
from datetime import datetime

class BotsWarehouse(orm.Model):
    _name = 'bots.warehouse'
    _inherit = 'bots.binding'
    _description = 'Bots Warehouse Mapping'

    _columns = {
        'name': fields.char('Name', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
    }

    _sql_constraints = [
        ('bots_warehouse_uniq', 'unique(backend_id, bots_id)',
         'A warehouse mapping with the same ID in Bots already exists.'),
        ('bots_warehouse_single', 'unique(backend_id)',
         'Multiple warehouses per Bots backend is not currently supported.'),
    ]

class BotsStockInventory(orm.Model):
    _name = 'bots.stock.inventory'
    _inherit = 'bots.binding'
    _inherits = {'stock.inventory': 'openerp_id'}
    _description = 'Bots Inventory'

    _columns = {
        'openerp_id': fields.many2one('stock.inventory',
                                      string='Stock Inventory',
                                      required=True,
                                      ondelete='restrict'),
        'warehouse_id': fields.many2one('bots.warehouse',
                                      string='Bots Warehouse',
                                      required=True,
                                      ondelete='restrict'),
        }

    _sql_constraints = [
        ('bots_inventory_uniq', 'unique(backend_id, openerp_id)',
         'A Bots inventory already exists for this inventory for the same backend.'),
    ]

@bots
class BotsWarehouseBinder(BotsModelBinder):
    _model_name = [
            'bots.warehouse',
        ]

@bots
class BotsStockInventoryBinder(BotsModelBinder):
    _model_name = [
            'bots.stock.inventory',
        ]

@bots
class BotsWarehouseImport(ImportSynchronizer):
    _model_name = ['bots.warehouse']

    def import_picking_confirmation(self, picking_types=('in', 'out'), new_cr=True):
        """
        Import the picking confirmation from Bots
        """
        self.backend_adapter.get_picking_conf(picking_types, new_cr=new_cr)

    def import_stock_levels(self, warehouse_id, new_cr=True):
        """
        Import the picking confirmation from Bots
        """
        self.backend_adapter.get_stock_levels(warehouse_id, new_cr=new_cr)

@bots
class WarehouseAdapter(BotsCRUDAdapter):
    _model_name = 'bots.warehouse'

    def get_picking_conf(self, picking_types, new_cr=True):
        product_binder = self.get_binder_for_model('bots.product')
        picking_in_binder = self.get_binder_for_model('bots.stock.picking.in')
        picking_out_binder = self.get_binder_for_model('bots.stock.picking.out')
        bots_picking_in_obj = self.session.pool.get('bots.stock.picking.in')
        bots_picking_out_obj = self.session.pool.get('bots.stock.picking.out')
        picking_obj = self.session.pool.get('stock.picking')
        bots_warehouse_obj = self.session.pool.get('bots.warehouse')
        wf_service = netsvc.LocalService("workflow")
        exceptions = []

        FILENAME = r'^picking_conf_.*\.json$'
        file_ids = self._search(FILENAME)
        res = []
        ctx = self.session.context.copy()
        ctx['wms_bots'] = True

        for file_id in file_ids:
            try:
                with file_to_process(self.session, file_id[0], new_cr=new_cr) as f:
                    json_data = json.load(f)
                    _cr = self.session.cr

                    json_data = json_data if type(json_data) in (list, tuple) else [json_data,]
                    for pickings in json_data:
                        for picking in pickings['orderconf']['shipment']:
                            if picking['type'] not in picking_types:
                                # We are not a picking we want to import, discarded
                                continue

                            if picking['type'] == 'in':
                                picking_binder = picking_in_binder
                                bots_picking_obj = bots_picking_in_obj
                            elif picking['type'] == 'out':
                                picking_binder = picking_out_binder
                                bots_picking_obj = bots_picking_out_obj
                            else:
                                raise NotImplementedError("Unable to import picking of type %s" % (picking['type'],))

                            picking_id = picking_binder.to_openerp(picking['id'])
                            if not picking_id:
                                raise NoExternalId("Picking %s could not be found in OpenERP" % (picking['id'],))
                            stock_picking = bots_picking_obj.browse(_cr, self.session.uid, picking_id, context=ctx)

                            tracking_number = False
                            for tracking in picking.get('references', []):
                                # Get the first sane tracking reference
                                tracking_code = tracking.get('id') or tracking.get('desc')
                                if tracking_code and tracking_code not in ('N/A',):
                                    if tracking['type'] == 'purchase_ref' and picking['type'] == 'in':
                                        tracking_number = tracking_code
                                    elif tracking['type'] == 'shipping_ref' and picking['type'] == 'out':
                                        tracking_number = tracking_code
                                    elif not tracking_number:
                                        tracking_number = tracking_code

                            if tracking_number:
                                bots_picking_obj.write(_cr, self.session.uid, picking_id, {'carrier_tracking_ref': tracking_number}, context=ctx)

                            if picking['confirmed'] not in ('Y', 'True', '1', True, 1):
                                # No more action needs to be taken, it is not yet delivered
                                continue

                            # Count products in the incoming file
                            prod_counts = {}
                            for line in picking['line']:
                                product_id = product_binder.to_openerp(line['product'])
                                if not product_id:
                                    raise NoExternalId("Product %s could not be found in OpenERP" % (line['product'],))
                                prod_counts[product_id] = prod_counts.get(product_id, 0) + int('qty_real' in line and line['qty_real'] or line['uom_qty'])

                            # Orgainise into done, partial and extra
                            moves_part = []
                            moves_extra = []
                            for move in stock_picking.move_lines:
                                qty = prod_counts.get(move.product_id.id, 0)
                                if qty >= int(move.product_qty):
                                    moves_part.append((move, int(move.product_qty)))
                                    qty -= int(move.product_qty)
                                elif qty > 0 and qty < int(move.product_qty) and int(move.product_qty) > 0:
                                    moves_part.append((move, qty))
                                    qty = 0
                                else:
                                    moves_part.append((move, 0))
                                    qty = 0
                                prod_counts[move.product_id.id] = qty

                            for prod, qty in prod_counts.iteritems():
                                if qty > 0:
                                    moves_extra.append((prod, qty))

                            # If extra, raise since we do not expect this
                            if moves_extra:
                                raise NotImplementedError("Unable to process unexpected incoming stock for %s: %s" % (picking['id'], moves_extra,))

                            # Prepare and complete the picking wizard
                            moves_to_ship = {}
                            for move, qty in moves_part:
                                moves_to_ship['move%s' % (move.id)] = {
                                    'product_id': move.product_id.id,
                                    'product_qty': qty,
                                    'product_uom': move.product_uom.id,
                                    'prodlot_id': move.prodlot_id.id,
                                }
                            split = picking_obj.do_partial(_cr, self.session.uid, [stock_picking.openerp_id.id], moves_to_ship, context=ctx)
                            stock_picking.refresh()

                            # If there is a backorder, we need to assert that the current picking remains available
                            # The backorder should be flagged for a checkpoint
                            if stock_picking.backorder_id:
                                if stock_picking.backorder_id.state != 'done' and stock_picking.state != 'assigned':
                                    raise JobError('Error while creating backorder for picking %s imported from Bots' % (stock_picking.name,))
                                add_checkpoint(self.session, stock_picking.openerp_id._name, stock_picking.openerp_id.id, self.backend_record.id)

            except Exception, e:
                # Log error then continue processing files
                exception = "Exception %s when processing file %s: %s" % (e, file_id[1], traceback.format_exc())
                exceptions.append(exception)
                pass

        # If we hit any errors, fail the job with a list of all errors now
        if exceptions:
            raise JobError('The following exceptions were encountered:\n\n%s' % ('\n\n'.join(exceptions),))

        return res

    def get_stock_levels(self, warehouse_id, new_cr=True):
        product_binder = self.get_binder_for_model('bots.product')
        inventory_binder = self.get_binder_for_model('bots.stock.inventory')
        bots_warehouse_obj = self.session.pool.get('bots.warehouse')
        product_obj = self.session.pool.get('product.product')
        inventory_obj = self.session.pool.get('stock.inventory')
        bots_inventory_obj = self.session.pool.get('bots.stock.inventory')
        exceptions = []

        FILENAME = r'^inventory_.*\.json$'
        file_ids = self._search(FILENAME)
        res = []
        warehouse = bots_warehouse_obj.browse(self.session.cr, self.session.uid, warehouse_id, self.session.context)


        for file_id in file_ids:
            try:
                with file_to_process(self.session, file_id[0], new_cr=new_cr) as f:
                    json_data = json.load(f)
                    _cr = self.session.cr

                    _session = ConnectorSession(self.session.cr, self.session.uid, context=self.session.context)
                    inventory_lines = {}
                    file_exceptions = []

                    json_data = json_data if type(json_data) in (list, tuple) else [json_data,]
                    for inventory in json_data:
                        for line in inventory['inventory']['inventory_line']:
                            product_id = product_binder.to_openerp(line['product'])
                            if not product_id:
                                file_exceptions.append(NoExternalId("Product %s could not be found in OpenERP" % (line['product'],)))
                                continue
                            # Check the stock level for this warehouse at this time
                            time = datetime.strptime(line['datetime'], '%Y-%m-%d %H:%M:%S')
                            if 'qty_total' in line and line['qty_total'].isdigit(): # Take the absolule stock in the warehouse
                                qty = int(line['qty_total'])
                            else: # Else if not available, work out from available + outgoing available
                                qty = int(line['qty_available'])
                                if 'qty_outgoing_available' in line and line['qty_outgoing_available'].isdigit():
                                    qty += int(line['qty_outgoing_available'])
                            if inventory_lines.setdefault(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT), {}).get('product_id', None):
                                file_exceptions.append(AssertionError("Product %s, ID %s appears twice in the inventory for %s" % (line['product'], product_id, time)))
                                continue
                            inventory_lines.setdefault(time.strftime(DEFAULT_SERVER_DATETIME_FORMAT), {})[product_id] = qty

                    if file_exceptions:
                        raise AssertionError("Errors were encountered on inventory import:\n%s" % ("\n".join([repr(x) for x in file_exceptions])))

                    inventory_lines = sorted(inventory_lines.items(), key=lambda x: x[0])
                    for time, products in inventory_lines:
                        inventory = {
                                'name': 'Bots - %s - %s' % (self.backend_record.name, time,),
                                'date': time,
                                'company_id': warehouse.warehouse_id.company_id.id,
                                'inventory_line_id': [],
                            }
                        for product_id, qty in products.iteritems():
                            location_id = warehouse.warehouse_id.lot_stock_id.id
                            ctx = {
                                    'location': location_id,
                                    'compute_child': False,
                                    #'to_date': time, # FIXME: Any recent inventories, even backdated, will not be considered since the date is always when it is done. Core bug or feature?
                                }
                            prod = product_obj.browse(_cr, self.session.uid, product_id, context=ctx)

                            if int(qty) == int(prod.qty_available):
                                # We match, no need to create an inventory line
                                continue

                            inventory_line = {
                                    'product_id': product_id,
                                    'location_id': location_id,
                                    'product_qty': int(qty),
                                    'product_uom': prod.uom_id.id, # We assume the qty is always in the standard UoM
                                }
                            inventory['inventory_line_id'].append([0, False, inventory_line])

                        if inventory['inventory_line_id']:
                            # We have a difference in inventory so we must create and validate a new inventory
                            inventory_id = inventory_obj.create(_cr, self.session.uid, inventory, context=self.session.context)
                            inventory_obj.action_confirm(_cr, self.session.uid, [inventory_id], context=self.session.context)
                            inventory_obj.action_done(_cr, self.session.uid, [inventory_id], context=self.session.context)
                            binding_id = bots_inventory_obj.create(_cr, self.session.uid,
                                {'backend_id': self.backend_record.id,
                                'openerp_id': inventory_id,
                                'warehouse_id': warehouse.id,
                                'bots_id': '%s %s' % (self.backend_record.name, time,),})
                            add_checkpoint(_session, 'stock.inventory', inventory_id, self.backend_record.id)

            except Exception, e:
                # Log error then continue processing files
                exception = "Exception %s when processing file %s: %s" % (e, file_id[1], traceback.format_exc())
                exceptions.append(exception)
                pass

        # If we hit any errors, fail the job with a list of all errors now
        if exceptions:
            raise JobError('The following exceptions were encountered:\n\n%s' % ('\n\n'.join(exceptions),))

        return res

@job
def import_stock_levels(session, model_name, record_id, new_cr=True):
    warehouse = session.browse(model_name, record_id)
    backend_id = warehouse.backend_id.id
    env = get_environment(session, model_name, backend_id)
    warehouse_importer = env.get_connector_unit(BotsWarehouseImport)
    warehouse_importer.import_stock_levels(record_id, new_cr=new_cr)
    return True

@job
def import_picking_confirmation(session, model_name, record_id, picking_types, new_cr=True):
    warehouse = session.browse(model_name, record_id)
    backend_id = warehouse.backend_id.id
    env = get_environment(session, model_name, backend_id)
    warehouse_importer = env.get_connector_unit(BotsWarehouseImport)
    warehouse_importer.import_picking_confirmation(picking_types=picking_types, new_cr=new_cr)
    return True
