# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bots open source edi translator
#    Copyright (C) 2014 credativ ltd (<http://www.credativ.co.uk>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

def main(inn,out):

    pinn = inn.getloop({'BOTSID': 'order'})
    lout = out.putloop({'BOTSID':'orderconf'})

    for pick in pinn:
        oout = lout.putloop({'BOTSID': 'orderconf'}, {'BOTSID':'shipment'})

        ORD_ID = pick.get({'BOTSID': 'order', 'internalPurchaseOrderRef': None})

        oout.put({'BOTSID':'shipment', 'id': ORD_ID})
        oout.put({'BOTSID':'shipment', 'confirmed': '1'})
        oout.put({'BOTSID':'shipment', 'type': 'in'})

        pinn_item = pick.getloop({'BOTSID': 'order'}, {'BOTSID': 'items'}, {'BOTSID': 'item'})
        for item in pinn_item:
            ORDL_PRODUCT = item.get({'BOTSID': 'item', 'sku': None})
            ORDL_STATUS = None
            ORDL_QTY = 0
            ORDL_DATETIME = None

            pinn_act = item.getloop({'BOTSID': 'item'}, {'BOTSID': 'actions'}, {'BOTSID': 'action'})
            for act in pinn_act:
                ACT_TYPE = act.get({'BOTSID': 'action', 'type': None})
                ACT_QTY = act.get({'BOTSID': 'action', 'qty': None})
                ACT_DATETIME = act.get({'BOTSID': 'action', 'date': None})

                # FIXME: Due to the inability to see if we have processed an action already (no unique ref) we will only take the last received action
                if ACT_TYPE == 'RECEIVED' and ACT_QTY: 
                    ORDL_STATUS = 'DONE'
                    ORDL_QTY = ACT_QTY
                    ORDL_DATETIME = ACT_DATETIME

            if ORDL_STATUS == 'DONE':
                olout = oout.putloop({'BOTSID': 'shipment'}, {'BOTSID':'line'})
                olout.put({'BOTSID':'line', 'type': 'in'})
                olout.put({'BOTSID':'line', 'status': ORDL_STATUS})
                olout.put({'BOTSID':'line', 'datetime': ORDL_DATETIME})
                olout.put({'BOTSID':'line', 'product': ORDL_PRODUCT})
                olout.put({'BOTSID':'line', 'qty_real': ACT_QTY})
