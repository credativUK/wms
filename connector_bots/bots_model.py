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

from openerp.osv import fields, orm
from .stock_warehouse import import_stock_levels, import_picking_confirmation
from openerp.addons.connector.session import ConnectorSession
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from datetime import datetime

class BotsBackend(orm.Model):
    _name = 'bots.backend'
    _description = 'Bots Backend'
    _inherit = 'connector.backend'

    _backend_type = 'bots'

    def _select_versions(self, cr, uid, context=None):
        return [('3.1.0', '3.1.0')]

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        'name_from': fields.char('Source ID', required=True, help='Name of the source location of the message, used for routing in Bots.'),
        'name_to': fields.char('Destination ID', required=True, help='Name of the destinations location of the message, used for routing in Bots.'),
        'location_in': fields.char('In Location', required=True, help='Location on the file system where incoming files are read from (Bots Out location)'),
        'location_archive': fields.char('Archive Location', required=True, help='Location on the file system where incoming files are archived after being read (Must be different to Bots archive location)'),
        'location_out': fields.char('Out Location', required=True, help='Location on the file system where outgoing files are written to (Bots In location)'),
        'warehouse_ids': fields.one2many('bots.warehouse', 'backend_id', string='Warehouse Mapping'),
        'feat_picking_out': fields.boolean('Export Delivery Orders', help='Export delivery orders for this warehouse'),
        'feat_picking_in': fields.boolean('Export Shipments', help='Export shipments for this warehouse'),
        'feat_picking_out_cancel': fields.boolean('Export Delivery Order Cancellations', help='Export delivery order cancellations for this warehouse'),
        'feat_picking_in_cancel': fields.boolean('Export Shipment Cancellations', help='Export shipment cancellations for this warehouse'),
        'feat_picking_out_conf': fields.boolean('Import Delivery Order Confirmation', help='Import delivery confirmation and tracking details for delivery orders'),
        'feat_picking_in_conf': fields.boolean('Import Shipment Confirmation', help='Import receipt confirmation for shipments'),
        'feat_inventory_in': fields.boolean('Import Inventory', help='Import inventories for this warehouse'),
        'feat_reexport_backorder': fields.boolean('Re-export Back Orders', help='When we receive a partial delivery from the 3PL,\n' \
                                                  'if True this will re-export the remaining undelivered stock,\n' \
                                                  'if False it will assume the 3PL is handling the remaining items and will send subsequent confirmations with the same order reference.'),
        'timezone': fields.char('Timezone', help='The timezone which will be used in incoming and outgoing messages'),
    }

    _defaults = {
        'feat_picking_out': True,
        'feat_picking_in': True,
        'feat_picking_out_cancel': False,
        'feat_picking_in_cancel': False,
        'feat_picking_out_conf': True,
        'feat_picking_in_conf': True,
        'feat_inventory_in': True,
        'feat_reexport_backorder': True,
    }

    def _bots_backend(self, cr, uid, callback, domain=None, context=None):
        if domain is None:
            domain = []
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

    def _scheduler_import_inventory(self, cr, uid, domain=None, new_cr=True, context=None):
        if not new_cr:
            self._bots_backend(cr, uid, self.import_inventory_test, domain=domain, context=context)
        else:
            self._bots_backend(cr, uid, self.import_inventory, domain=domain, context=context)

    def _scheduler_import_stock_picking_out_conf(self, cr, uid, domain=None, new_cr=True, context=None):
        if not new_cr:
            self._bots_backend(cr, uid, self.import_picking_test, domain=domain, context=context)
        else:
            self._bots_backend(cr, uid, self.import_picking, domain=domain, context=context)

    def _scheduler_import_stock_picking_in_conf(self, cr, uid, domain=None, new_cr=True, context=None):
        if not new_cr:
            self._bots_backend(cr, uid, self.import_picking_test, domain=domain, context=context)
        else:
            self._bots_backend(cr, uid, self.import_picking, domain=domain, context=context)

    def import_inventory_test(self, cr, uid, ids, context=None):
        return self.import_inventory(cr, uid, ids, new_cr=False, context=context)

    def import_inventory(self, cr, uid, ids, new_cr=True, context=None):
        """ Import inventory from all warehouses """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        warehouse_obj = self.pool.get('bots.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [('backend_id', 'in', ids)], context=context)
        warehouses = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
        for warehouse in warehouses:
            if warehouse.backend_id.feat_inventory_in:
                session = ConnectorSession(cr, uid, context=context)
                import_stock_levels.delay(session, 'bots.warehouse', warehouse.id, new_cr=new_cr)
        return True

    def import_picking_test(self, cr, uid, ids, context=None):
        return self.import_picking(cr, uid, ids, new_cr=False, context=context)

    def import_picking(self, cr, uid, ids, new_cr=True, context=None):
        """ Import Picking confirmations """
        if not hasattr(ids, '__iter__'):
            ids = [ids]
        warehouse_obj = self.pool.get('bots.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [('backend_id', 'in', ids)], context=context)
        warehouses = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
        for warehouse in warehouses:
            picking_types = []
            if warehouse.backend_id.feat_picking_in_conf:
                picking_types.append('in')
            if warehouse.backend_id.feat_picking_out_conf:
                picking_types.append('out')
            if picking_types:
                session = ConnectorSession(cr, uid, context=context)
                import_picking_confirmation.delay(
                    session, 'bots.warehouse', warehouse.id, picking_types, new_cr=new_cr, priority=5
                )
        return True

    def datetime_convert(self, cr, uid, ids, dt=None, context=None):
        for backend in self.browse(cr, uid, ids, context=context):
            if backend.timezone in pytz.all_timezones:
                if len(dt) == 19:
                    datetime_utc = pytz.utc.localize(datetime.strptime(dt, DEFAULT_SERVER_DATETIME_FORMAT))
                    return datetime_utc.astimezone(pytz.timezone(backend.timezone)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return dt

class BotsFile(orm.TransientModel):
    _name = 'bots.file'
    _description = 'File mutex for communication with Bots'
    _rec_name = 'full_path'

    _columns = {
        'full_path': fields.char('Full Path', required=True),
        'temp_path': fields.char('Temporary/Archive Path', required=True),
        'arch_path': fields.char('Archive Path', required=True),
        'processed': fields.boolean('Already processed'),
    }

    _sql_constraints = [
        ('bots_file_uniq', 'unique(full_path)', 'A file already exists at this path.'),
        ('bots_temp_file_uniq', 'unique(temp_path)', 'A file already exists at this path.'),
        ('bots_arch_file_uniq', 'unique(arch_path)', 'A file already exists at this path.'),
    ]
