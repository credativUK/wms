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

from .unit.binder import BotsBinder
from .backend import bots

import logging
_logger = logging.getLogger(__name__)

class ProductProduct(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'magento_prism_sku': fields.char('Prism SKU'),
        'magento_commodity_code': fields.char('Customs Commodity Code'),
    }

@bots
class BotsProductBinder(BotsBinder):
    _model_name = [
            'bots.product',
        ]

    def to_openerp(self, external_id, unwrap=False):
        '''Match the SKU from Bots to the OpenERP product. Since product master sync is not yet implemented we will attempt to match directly on SKU with overrides'''
        # Attempt to get overriding mappings
        bots_product_ids = self.session.search('bots.product', [('bots_id', '=', str(external_id)), ('backend_id', '=', self.backend_record.id)])
        if bots_product_ids:
            bots_product_data = self.session.read('bots.product', bots_product_ids, ['product_id'])
            binding_ids = [x['product_id'][0] for x in bots_product_data]
        else:
            # If no overriding mappings, try to match the SKU directly
            binding_ids = self.session.search('product.product', [('magento_prism_sku', '=', str(external_id))])
            if not binding_ids:
                binding_ids = self.session.search('product.product', [('default_code', '=', str(external_id))])
        if not binding_ids:
            return None
        if len(binding_ids) > 1:
            _logger.warning('Found multiple OpenERP IDs for product with Bots SKU %s' % (external_id,))
        binding_id = binding_ids[0]
        if unwrap:
            return self.session.read('product.product', binding_id, ['openerp_id'])['openerp_id'][0]
        else:
            return binding_id

    def to_backend(self, record_id, wrap=False):
        '''Export the SKU to Bots from the OpenERP product. Since product master sync is not yet implimented we will attempt to match directly on SKU with overrides'''

        # Attempt to get overriding mappings
        bots_product_ids = self.session.search('bots.product', [('product_id', '=', record_id), ('backend_id', '=', self.backend_record.id)])
        if bots_product_ids:
            bots_record = self.session.read('bots.product', bots_product_ids[0], ['bots_id'])['bots_id']
        else:
            values = self.session.read("product.product", record_id, ['default_code', 'magento_prism_sku'])
            bots_record = values.get('magento_prism_sku') or values.get('default_code')
        return bots_record
