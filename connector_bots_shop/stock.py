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

from openerp.addons.connector_wms.event import on_picking_out_done


def picking_done(session, model_name, record_id, picking_type, location_type):
    warehouse_obj = session.pool.get('stock.warehouse')
    bots_warehouse_obj = session.pool.get('bots.warehouse')
    picking = session.browse(model_name, record_id)
    # Check to see if the picking should be exported to the WMS
    # If so create binding, else return
    if not picking.state == 'done':  # Handle only deliveries which are complete
        return

    sale_id = picking.sale_id and picking.sale_id.id or False
    sale_backend_id = False
    if sale_id:
        bots_sale_obj = session.pool.get('bots.sale.order')
        bots_sale_id = bots_sale_obj.search(session.cr, session.uid, [('openerp_id','=',sale_id)]) # FIXME: Match backend as well as ID for multi-backend support
        bots_sales = bots_sale_obj.browse(session.cr, session.uid, bots_sale_id)

         # Ensure never more than 1 matching bots sale order
        assert len(bots_sales) <= 1
        if len(bots_sales) == 0:
            return

        sale_backend_id = bots_sales[0].backend_id and bots_sales[0].backend_id.id or False
        if not sale_backend_id: # Do not export picking if not linked to imported sale order
            return

    location_ids = []
    if location_type == 'src':
        location = picking.location_id or picking.move_lines and picking.move_lines[0].location_id
        while location and location.id not in location_ids:
            location_ids.append(location.id)
            if location.chained_picking_type != 'in' and location.chained_auto_packing == 'auto':
                location = location.chained_location_id
    else:
        location = picking.location_dest_id or picking.move_lines and picking.move_lines[0].location_dest_id
        while location and location.id not in location_ids:
            location_ids.append(location.id)
            if location.chained_picking_type != 'out' and location.chained_auto_packing == 'auto':
                location = location.chained_location_id

    warehouse_ids = []
    for location_id in location_ids:
        warehouse_ids = warehouse_obj.search(session.cr, session.uid, ['|', ('lot_stock_id', '=', location_id), ('lot_output_id', '=', location_id)])
        if warehouse_ids:
            break

    bots_warehouse_ids = bots_warehouse_obj.search(session.cr, session.uid, [('warehouse_id', 'in', warehouse_ids)])
    bots_warehouse = bots_warehouse_obj.browse(session.cr, session.uid, bots_warehouse_ids)
    for warehouse in bots_warehouse:
        backend_id = warehouse.backend_id
        # Make sure picking sale backend matches picking warehouse backend before exporting
        if (sale_backend_id and sale_backend_id == backend_id.id) and (picking_type == 'bots.stock.picking.out' and backend_id.feat_export_picking_out_when_done):
            #or (picking_type == 'bots.stock.picking.in' and backend_id.feat_export_picking_in_when_done): # NotImplemented
            session.create(picking_type,
                            {'backend_id': backend_id.id,
                            'openerp_id': picking.id,
                            'warehouse_id': warehouse['id'],})
            # Creation will trigger on_record_create with export_picking function
        
@on_picking_out_done
def picking_out_done(session, model_name, record_id):
    return picking_done(session, model_name, record_id, 'bots.stock.picking.out', location_type='src')
