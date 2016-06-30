# -*- coding: utf-8 -*-
# (c) 2016 credativ ltd. - Ondřej Kuzník
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp.osv import orm

from openerp.addons.queue_tasks.queue_task import defer

class PurchaseOrder(orm.Model):
    _inherit = 'purchase.order'

    @defer("Cut-off Purchase Order")
    def purchase_cutoff_defer(self, cr, uid, ids, context=None):
        warehouse_pool = self.pool.get('bots.warehouse')
        for group in self.read_group(cr, uid, [('id', 'in', ids)], ['warehouse_id'], ['warehouse_id'], context=context):
            warehouse = warehouse_pool.browse(cr, uid, group['warehouse_id'][0], context=context)
            purchase_ids = self.search(cr, uid, group['__domain'], context=context)
            warehouse.purchase_cutoff(purchase_ids)
