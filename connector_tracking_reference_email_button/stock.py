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


from osv import osv, fields


class StockPickingOut(osv.Model):

    _inherit = 'stock.picking.out'


    def action_track_ref_send(self, cr, uid, ids, context=None):
        data_obj = self.pool.get('ir.model.data')
        email_ids = data_obj.search(cr, uid, [('model', '=', 'email.template'), ('name', '=', 'track_reference_template')])
        template_id = email_ids and data_obj.read(cr, uid, email_ids[0], ['res_id'], context=context)['res_id'] or False

        try:                                          
            compose_form_id = data_obj.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:                            
            compose_form_id = False

        ctx = dict(context)
        ctx.update({
            'default_model'            : 'stock.picking',
            'default_res_id'           : ids[0],
            'default_use_template'     : bool(template_id),
            'default_template_id'      : template_id,
            'default_composition_mode' : 'comment',
            'mark_so_as_sent'          : True,
        })
        return {
            'type'      : 'ir.actions.act_window',
            'view_type' : 'form',
            'view_mode' : 'form',
            'res_model' : 'mail.compose.message',
            'views'     : [(compose_form_id, 'form')],
            'view_id'   : compose_form_id,
            'target'    : 'new',
            'context'   : ctx,
        }

