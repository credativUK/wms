# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2016 credativ Ltd
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

from openerp.addons.connector_bots.backend import bots
from openerp.addons.connector_bots.stock import StockPickingOutAdapter

@bots(replacing=StockPickingOutAdapter)
class MagentoBundlePickingOutAdapter(StockPickingOutAdapter):
    _model_name = 'bots.stock.picking.out'
    _picking_type = 'out'

    def _get_moves_to_split(self, pick, allowed_states):
        """ If a move belonging to a bundle is split out,
            the rest of the bundle should be split out also.
        """
        res = super(MagentoBundlePickingOutAdapter, self)._get_moves_to_split(pick, allowed_states)
        moves_to_split, picking_complete = res 
        moves_to_split = set(moves_to_split)

        product_binder = self.get_binder_for_model('bots.product')
        pick_obj = self.session.pool.get('stock.picking')
        bundles = pick_obj.to_bundles(self.session.cr, self.session.uid, pick.openerp_id.id)[0]

        for bundle in bundles.values():
            for move in bundle:
                if move.id in moves_to_split and move.state != 'cancel':
                    moves_to_split = moves_to_split.union([m.id for m in bundle])

        moves_to_split = list(moves_to_split)

        # picking_complete should still be accurate
        return moves_to_split, picking_complete
