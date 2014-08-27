# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Ondrej Kuznik
#    Copyright 2014 credativ ltd.
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

from openerp.osv import orm

class magento_product_product(orm.Model):
    _inherit = 'magento.product.product'

    def _magento_qty(self, cr, uid, product, context=None):
        if context is None:
            context = {}
        backend = product.backend_id
        if backend.product_stock_field_id:
            stock_field = backend.product_stock_field_id.name
        else:
            stock_field = 'virtual_available'

        product_stk = 0
        for warehouse in [backend.warehouse_id] + backend.warehouse_ids:
            stock = warehouse.lot_stock_id

            location_ctx = context.copy()
            location_ctx['location'] = stock.id
            product_stk += self.read(cr, uid, product.id,
                                    [stock_field],
                                    context=location_ctx)[stock_field]

        return product_stk
