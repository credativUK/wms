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

from openerp.osv import orm

from openerp.addons.connector.session import ConnectorSession
from .event import on_picking_out_send_email

import sys
import logging
_logger = logging.getLogger(__name__)

@on_picking_out_send_email
def picking_out_send_email(session, model_name, record_id):
    """Send email to customer when picking is done.

    @return: True
    """

    ir_model_data = session.pool.get('ir.model.data')
    action_server_pool = session.pool.get('ir.actions.server')
    server_action_id = ir_model_data.get_object_reference(session.cr, session.uid, 'connector_auto_dispatch_email', 'action_dispatch_email')
    context = {'active_id':record_id,'active_ids':[record_id]}
    if server_action_id:
        action_server_pool.run(session.cr, session.uid, [server_action_id[1]], context)
    else:
        _logger.error("Dispatch email template not found. Email couldn't be send.")
    return True

class stock_picking(orm.Model):
    _inherit = 'stock.picking'

    def action_done(self, cr, uid, ids):
        """Changes picking state to done.

        This method is called at the end of the workflow by the activity "done".
        @return: True
        """

        res = super(stock_picking, self).action_done(cr, uid, ids)
        if res:
            session = ConnectorSession(cr, uid, context=None)
            picking_records = self.read(cr, uid, ids,
                                    ['id', 'type'],
                                    context=None)
            for picking_vals in picking_records:
                if picking_vals['type'] == 'out':
                    on_picking_out_send_email.fire(session, self._name, picking_vals['id'])
                else:
                    continue
        return res

    def send_dispatch_email(self, cr, uid, ids, context=None):
        '''Send email to customers'''

        ir_model_data = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        if not ids:
            ids = context.get('active_id',[]) and [context['active_id']]
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'connector_auto_dispatch_email', 'email_template_dispatch_customer')[1]
            for record_id in ids:
                self.pool.get('email.template').send_mail(cr, uid, template_id, record_id, force_send=True, context=context)
        except:
            _logger.error(sys.exc_info()[0])



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
