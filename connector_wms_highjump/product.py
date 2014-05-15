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

_logger = logging.getLogger(__name__)

class highjump_product_product(orm.TransientModel):
    _name = 'highjump.product.product'
    _inherit = 'highjump.binding'
    _inherits = {'product.product': 'openerp_id'}
    _description = 'High Jump Product'

    _columns = {
        'openerp_id': fields.many2one('product.product',
                                      string='Product',
                                      required=True,
                                      ondelete='restrict'),
        }

@highjump
class HighJumpProductBinder(HighJumpBinder):
    _model_name = [
            'highjump.product.product',
        ]

    def to_openerp(self, external_id, unwrap=False):
        '''Match the SKU from High Jump to the OpenERP product. Since the API does not
        support product master sync we will attempt to match directly on SKU with overrides'''
        # Attempt to get overriding mappings
        hj_product_ids = self.session.search('highjump.product', [('highjump_id', '=', str(external_id)), ('backend_id', '=', self.backend_record.id)])
        if hj_product_ids:
            hj_product_data = self.session.read('highjump.product', hj_product_ids, ['product_id'])
            binding_ids = [x['product_id'][0] for x in hj_product_data]
        else:
            # If no overriding mappings, try to match the SKU directly
            binding_ids = self.session.search('product.product', [('default_code', '=', str(external_id))])
        if not binding_ids:
            return None
        if len(binding_ids) > 1:
            _logger.warning('Found multiple OpenERP IDs for product with HighJump SKU %s' % (external_id,))
        binding_id = binding_ids[0]
        if unwrap:
            return self.session.read('product.product', binding_id, ['openerp_id'])['openerp_id'][0]
        else:
            return binding_id

    def to_backend(self, record_id, wrap=False):
        '''Export the SKU to High Jump from the OpenERP product. Since the API does not
        support product master sync we will attempt to match directly on SKU with overrides'''

        # Attempt to get overriding mappings
        hj_product_ids = self.session.search('highjump.product', [('product_id', '=', record_id), ('backend_id', '=', self.backend_record.id)])
        if hj_product_ids:
            highjump_record = self.session.read('highjump.product', hj_product_ids[0], ['highjump_id'])['highjump_id']
        else:
            highjump_record = self.session.read("product.product", record_id, ['default_code'])['default_code']
        return highjump_record

    def bind(self, external_id, binding_id):
        raise NotImplementedError
