# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 credativ Ltd
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

import logging
_logger = logging.getLogger(__name__)


class ProductProduct(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'exclude_from_bots_stock': fields.boolean(
            'Exclude from Bots stock export',
            required=False,
            help="Check this to exclude the product from stock exports to Bots."),
        }

    _defaults = {
        'exclude_from_bots_stock': False,
        }
