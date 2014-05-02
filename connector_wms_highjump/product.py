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
        binding_ids = self.session.search('product.product', [('default_code', '=', str(external_id))])
        if not binding_ids:
            return None
        assert len(binding_ids) == 1, "Several records found: %s" % binding_ids
        binding_id = binding_ids[0]
        if unwrap:
            return self.session.read('product.product', binding_id, ['openerp_id'])['openerp_id'][0]
        else:
            return binding_id

    def to_backend(self, record_id, wrap=False):
        highjump_record = self.session.read("product.product", record_id, ['default_code'])
        assert highjump_record
        return highjump_record['default_code']

    def bind(self, external_id, binding_id):
        raise NotImplementedError
