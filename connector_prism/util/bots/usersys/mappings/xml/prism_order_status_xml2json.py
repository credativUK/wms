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

import re


CARRIER_MAPING = {
    'RM': 'Royal Mail Untracked',
    'FJ77': 'Royal Mail Tracked',
    'FL72': 'Royal Mail Tracked',
    'BL': 'By Courier',
    '4757': 'FedEx (Express)',
    '8JF': 'HDNL Courier',
    '81RQ': 'Collect+',
    '1550': 'DPD',
}
CARRIER_DEFAULT = ''

def main(inn,out):

    pinn = inn.getloop({'BOTSID': 'order'})
    lout = out.putloop({'BOTSID':'orderconf'})

    for pick in pinn:
        oout = lout.putloop({'BOTSID': 'orderconf'}, {'BOTSID':'shipment'})

        ORD_ID = pick.get({'BOTSID': 'order', 'orderNumber': None})

        oout.put({'BOTSID':'shipment', 'id': ORD_ID})
        oout.put({'BOTSID':'shipment', 'confirmed': '1'})
        oout.put({'BOTSID':'shipment', 'type': 'out'})

        pinn_item = pick.getloop({'BOTSID': 'order'}, {'BOTSID': 'items'}, {'BOTSID': 'item'})
        ORD_PRODUCTS = {}
        ORD_TRACKING = []
        ORD_CARRIER = ''
        for item in pinn_item:
            ORDL_PRODUCT = item.get({'BOTSID': 'item', 'productCode': None})
            ORDL_STATUS = item.get({'BOTSID': 'item', 'status': None})
            ORDL_DATETIME = item.get({'BOTSID': 'item', 'statusDate': None})

            if ORDL_STATUS == 'DESPATCHED':
                ORDL_STATUS = 'DONE' # Remap to more standard done

            ORDL_QTY = ORD_PRODUCTS.setdefault((ORDL_PRODUCT, ORDL_STATUS), {}).get('QTY', 0) + 1
            ORD_PRODUCTS[(ORDL_PRODUCT, ORDL_STATUS)]['DATETIME'] = ORDL_DATETIME
            ORD_PRODUCTS[(ORDL_PRODUCT, ORDL_STATUS)]['QTY'] = ORDL_QTY

            LINE_INTERNAL_IDS = set(ORD_PRODUCTS[(ORDL_PRODUCT, ORDL_STATUS)].get('LINE_INTERNAL_IDS', []))
            pinn_attr = item.getloop({'BOTSID': 'item'}, {'BOTSID': 'attributes'}, {'BOTSID': 'attribute'})
            for attr in pinn_attr:
                ATTR_NAME = attr.get({'BOTSID': 'attribute', 'name': None})
                ATTR_VALUE = attr.get({'BOTSID': 'attribute', 'value': None})

                if ATTR_NAME == 'trackingReference' and ATTR_VALUE:
                    if ATTR_VALUE not in ORD_TRACKING:
                        ORD_TRACKING.append(ATTR_VALUE)
                    if not ORD_CARRIER and ATTR_VALUE:
                        for prefix, carrier in CARRIER_MAPING.iteritems():
                            if ATTR_VALUE.startswith(prefix):
                                ORD_CARRIER = carrier
                                break
                if ATTR_NAME == 'uniqueRecordID' and ATTR_VALUE:

                    LINE_INTERNAL_ID = re.match("^[1-9]+0+M?(\d+)$", ATTR_VALUE)

                    if LINE_INTERNAL_ID:
                        LINE_INTERNAL_IDS.add(LINE_INTERNAL_ID.groups()[0])

            ORD_PRODUCTS[(ORDL_PRODUCT, ORDL_STATUS)]['LINE_INTERNAL_IDS'] = list(LINE_INTERNAL_IDS)

        for (LINE_PRODUCT, LINE_STATUS), LINE_DATA in ORD_PRODUCTS.iteritems():
            olout = oout.putloop({'BOTSID': 'shipment'}, {'BOTSID':'line'})
            olout.put({'BOTSID':'line', 'type': 'out'})
            olout.put({'BOTSID':'line', 'status': LINE_STATUS})
            olout.put({'BOTSID':'line', 'datetime': LINE_DATA.get('DATETIME')})
            olout.put({'BOTSID':'line', 'product': LINE_PRODUCT})
            olout.put({'BOTSID':'line', 'qty_real': LINE_DATA.get('QTY')})
            if LINE_DATA.get('LINE_INTERNAL_IDS'):
                olout.put({'BOTSID':'line', 'move_ids': ','.join(LINE_DATA.get('LINE_INTERNAL_IDS', []))})

        if ORD_TRACKING:
            oout.put({'BOTSID':'shipment', 'tracking_number': ','.join(ORD_TRACKING)})
            oout.put({'BOTSID':'shipment', 'carrier': ORD_CARRIER or CARRIER_DEFAULT})
