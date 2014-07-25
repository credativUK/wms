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
    }

    _defaults = {
        'feat_picking_out': True,
        'feat_picking_in': True,
        'feat_picking_out_cancel': True,
        'feat_picking_in_cancel': True,
        'feat_picking_out_conf': True,
        'feat_picking_in_conf': True,
        'feat_inventory_in': True,
    }

    def _bots_backend(self, cr, uid, callback, domain=None, context=None):
        if domain is None:
            domain = []
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            callback(cr, uid, ids, context=context)

class BotsFile(orm.TransientModel):
    _name = 'bots.file'
    _description = 'File mutex for communication with Bots'
    _rec_name = 'full_path'

    _columns = {
        'full_path': fields.char('Full Path', required=True),
        'temp_path': fields.char('Temporary Path', required=True),
    }

    _sql_constraints = [
        ('bots_file_uniq', 'unique(full_path)', 'A file already exists at this path.'),
        ('bots_temp_file_uniq', 'unique(temp_path)', 'A file already exists at this path.'),
    ]

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
    ]

class BotsProduct(orm.Model):
    _name = 'bots.product'
    _inherit = 'bots.binding'
    _description = 'Bots Product Mapping'

    _columns = {
        'name': fields.char('Name', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
    }

    _sql_constraints = [
        ('bots_product_uniq', 'unique(backend_id, bots_id)',
         'A product mapping with the same ID in Bots already exists.'),
    ]
