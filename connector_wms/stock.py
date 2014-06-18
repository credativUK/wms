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

from openerp.osv import orm,osv

from openerp.addons.connector.session import ConnectorSession
from .event import on_picking_out_available


def send_email(session, module_name, template_name, record_ids,context=None):
    '''Send email to customers'''

    ir_model_data = session.pool.get('ir.model.data')
    if context is None:
        context = {}
    try:
        template_id = ir_model_data.get_object_reference(session.cr, session.uid, module_name,template_name)[1]
        for record_id in record_ids:
            session.pool.get('email.template').send_mail(session.cr, session.uid, template_id, record_id, force_send=True, context=context)
    except ValueError:
        #TODO Log exception
        pass

class stock_picking(orm.Model):
    _inherit = 'stock.picking'

    def action_assign_wkf(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_assign_wkf(cr, uid, ids, context=context)
        if res:
            session = ConnectorSession(cr, uid, context=context)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type'],
                                    context=context)
            for picking_vals in picking_records:
                if picking_vals['type'] != 'out':
                    continue
                on_picking_out_available.fire(session, self._name, picking_vals['id'])
        return res


    def action_assign(self, cr, uid, ids, *args):
        res = super(stock_picking, self).action_assign(cr, uid, ids, *args)
        if res:
            session = ConnectorSession(cr, uid, context=None)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type'],
                                    context=None)
            for picking_vals in picking_records:
                if picking_vals['type'] != 'out':
                    continue
                on_picking_out_available.fire(session, self._name, picking_vals['id'])
        return res

    def action_done(self, cr, uid, ids, context=None):
        """Changes picking state to done.

        This method is called at the end of the workflow by the activity "done".
        @return: True
        """

        res = super(stock_picking, self).action_done(cr, uid, ids, context=context)
        session = ConnectorSession(cr, uid, context=context)
        #If sale order associated with picking then send email
        for picking in self.browse(cr,uid,ids,context=context):
            if picking.sale_id:
                send_email(session, 'connector_wms', 'email_template_dispatch_customer', ids, context=context)
        return res