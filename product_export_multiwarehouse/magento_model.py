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

from openerp.osv import orm, fields

class magento_backend(orm.Model):
    _inherit = 'magento.backend'

    _columns = {
        'warehouse_ids': fields.many2many('stock.warehouse', 'magento_backend_warehouse_rel',
                                        'backend_id', 'warehouse_id', 'Additional Warehouses',
                                        help='Warehouse whose stock is added to exported '
                                             'stock quantities.'),
    }
