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
from openerp.addons.connector.exception import JobError, NoExternalId, MappingError

from openerp.addons.connector_bots.backend import bots
from openerp.addons.connector_bots.connector import get_environment

import json
import traceback
from datetime import datetime
import re

from openerp.addons.connector_bots.stock import (StockPickingOutAdapter, StockPickingInAdapter, BotsPickingExport)

@job
def export_picking_crossdock(session, model_name, record_id):
    picking = session.browse(model_name, record_id)
    if picking.state == 'done' and session.search(model_name, [('backorder_id', '=', picking.openerp_id.id)]):
        # We are an auto-created back order completed - ignore this export
        return "Not exporting crossdock for auto-created done picking backorder %s" % (picking.name,)
    backend_id = picking.backend_id.id
    env = get_environment(session, model_name, backend_id)
    picking_exporter = env.get_connector_unit(BotsPickingExport)
    res = picking_exporter.run_crossdock(record_id)
    return res

@bots(replacing=StockPickingInAdapter)
class PrismPickingInAdapter(StockPickingInAdapter):
    _picking_type = None
    _model_name = 'bots.stock.picking.in'
    _picking_type = 'in'

    def _prepare_create_data(self, picking_id):
        data, FILENAME, bots_id = super(PrismPickingInAdapter, self)._prepare_create_data(picking_id)

        move_obj = self.session.pool.get('stock.move')

        cross_dock = 0
        for line in data['picking']['pickings'][0].get('line', []):
            if line.get('move_id'):
                move = move_obj.browse(self.session.cr, self.session.uid, line.get('move_id'))
                cross_dock = move.purchase_line_id.order_id.bots_cross_dock and 1 or 0

        data['picking']['pickings'][0].update({'crossdock': cross_dock})
        return data, FILENAME, bots_id

@bots(replacing=StockPickingOutAdapter)
class PrismPickingOutAdapter(StockPickingOutAdapter):
    _picking_type = None
    _model_name = 'bots.stock.picking.out'
    _picking_type = 'out'

    def _prepare_create_data(self, picking_id):
        data, FILENAME, bots_id = super(PrismPickingOutAdapter, self)._prepare_create_data(picking_id)

        move_obj = self.session.pool.get('stock.move')

        for line in data['picking']['pickings'][0].get('line', []):
            if line.get('move_id'):
                move = move_obj.browse(self.session.cr, self.session.uid, line.get('move_id'))
                line.update({'customs_commodity_code': move.product_id.magento_commodity_code or '0',})

        return data, FILENAME, bots_id

    def create(self, picking_id):
        res = super(PrismPickingOutAdapter, self).create(picking_id)
        picking = self.session.browse('bots.stock.picking.out', picking_id)
        if picking.backend_id.feat_picking_out_crossdock and picking.type == 'out':
            export_picking_crossdock.delay(self.session, 'bots.stock.picking.out', picking_id)
        return res

    def _prepare_crossdock(self, picking_id):
        picking_binder = self.get_binder_for_model('bots.stock.picking.in')
        bots_picking_obj = self.session.pool.get('bots.stock.picking.out')
        move_obj = self.session.pool.get('stock.move')
        purchase_line_obj = self.session.pool.get('purchase.order.line')

        picking = bots_picking_obj.browse(self.session.cr, self.session.uid, picking_id)

        if not picking.bots_id:
            raise JobError(_('The Bots picking %s is not exported. A join file cannot be exported for it.') % (picking.id,))

        order_lines = []
        for move in picking.move_lines:
            if move.state not in ('waiting', 'confirmed', 'assigned',):
                raise MappingError(_('Unable to export cross-dock details for a move which is in state %s.') % (move.state,))

            po_name = ""
            pol_ids = purchase_line_obj.search(self.session.cr, self.session.uid, [('move_dest_id', '=', move.id),
                                                                                   ('state', '!=', 'cancel'),
                                                                                   ('order_id.state', '!=', 'cancel'),
                                                                                   ('product_id', '=', move.product_id.id)], context=self.session.context)
            if len(pol_ids) > 1:
                raise MappingError(_('Unable to export cross-dock details for a move which is incorrectly linked to multiple purchases %s.') % (move.id,))
            elif len(pol_ids) == 1:
                move_ids = move_obj.search(self.session.cr, self.session.uid, [('move_dest_id', '=', move.id),
                                                                               ('purchase_line_id', '=', pol_ids[0]),
                                                                               ('state', '!=', 'cancel')], context=self.session.context)
                if move_ids:
                    move_po = move_obj.browse(self.session.cr, self.session.uid, move_ids[0], self.session.context)
                    # We cannot cross-dock a PO which has already been received into the warehouse, eg "deliver at once" stock
                    if move_po.picking_id and not move_po.state == 'done':
                        po_name = picking_binder.to_backend(move_po.picking_id.id, wrap=True) or ""
                        if not po_name:
                            raise NoExternalId("No PO ID found, try again later")

            order_line = {
                    "move_id": move.id,
                    "product_qty": int(move.product_qty),
                    "po_id": po_name,
                }
            order_lines.append(order_line)

        if not order_lines:
            raise MappingError(_('Unable to export any cross dock lines on export of Bots picking %s.') % (picking_id,))

        data = {
                'crossdock': {
                        'crossdock_line': order_lines,
                        'header': [{
                                'partner_to': picking.backend_id.name_to,
                                'partner_from': picking.backend_id.name_from,
                                'message_id': '0',
                                'date_msg': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                            }],
                    },
                }
        FILENAME = 'cross_dock_%s.json'
        return data, FILENAME

    def create_crossdock(self, picking_id):
        data, FILENAME = self._prepare_crossdock(picking_id)
        data = json.dumps(data, indent=4)
        filename_id = self._get_unique_filename(FILENAME)
        res = self._write(filename_id, data)
        return

@bots(replacing=BotsPickingExport)
class PrismBotsPickingExport(BotsPickingExport):

    def run(self, binding_id):
        # Check if we are a PO edit and if the original already has a binding - use this instead if PO edits are not supported
        if self.model._name == 'bots.stock.picking.in' and self.backend_record.feat_picking_in_cancel != 'export':
            picking = self.model.browse(self.session.cr, self.session.uid, binding_id).openerp_id
            if picking.purchase_id and picking.purchase_id.order_edit_id:
                old_binding_ids = self.model.search(self.session.cr, self.session.uid, [('purchase_id', '=', picking.purchase_id.order_edit_id.id), ('bots_id', '!=', False)])
                if old_binding_ids:
                    bots_id = self.model.browse(self.session.cr, self.session.uid, old_binding_ids).bots_id
                    self.model.unlink(self.session.cr, self.session.uid, old_binding_ids)
                    self.model.write(self.session.cr, self.session.uid, old_binding_ids, {'bots_id': bots_id})
                    return
        # Else create a new binding
        return super(PrismBotsPickingExport, self).run(binding_id)

    def run_crossdock(self, binding_id):
        """
        Export the picking crossdock to Bots
        """
        self.backend_adapter.create_crossdock(binding_id)
