# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bots open source edi translator
#    Copyright (C) 2015 credativ ltd (<http://www.credativ.co.uk>). All Rights Reserved
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

def main(inn,out):

    pinn = inn.getloop({'BOTSID': 'picking'}, {'BOTSID': 'pickings'})
    main_out = out.putloop({'BOTSID': 'pos'})
    for pick in pinn:
        # == MAIN ORDER ==
        ORD_ID = pick.get({'BOTSID': 'pickings', 'id': None})
        assert ORD_ID, "Order ID must be present"
        ORD_ID = re.sub(r'[\\/_-]', r'', ORD_ID.upper())
        ORD_STATE = pick.get({'BOTSID': 'pickings', 'state': None})

        if ORD_STATE == 'delete': # Ignore cancelled orders, not supported
            continue
        elif ORD_STATE != 'new': # Raise on other order state
            raise NotImplementedError('Unable to handle order with state %s' % (ORD_STATE,))

        PART_CODE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'code': None})
        PART_COUNTRY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'country': None})
        ORD_REMARK = pick.get({'BOTSID': 'pickings', 'desc': None})
        ORD_TYPE = pick.get({'BOTSID': 'pickings', 'crossdock': None}) == "1" and 'XDOCK' or 'STORAGE'
        ORD_DELIVERY_DATE = pick.get({'BOTSID': 'pickings', 'date': None})
        ORDER_ATTRS = {}

        order_out = main_out.putloop({'BOTSID': 'pos'}, {'BOTSID':'po'})

        # == LINES ==

        ORD_ITEMS = 0
        ORD_TOTAL = 0.0
        ORD_LINES = 0
        ORD_CURRENCY = None
        plines = pick.getloop({'BOTSID': 'pickings'}, {'BOTSID': 'line'})

        lines = {}
        for pline in plines:
            LINE_ID = pline.get({'BOTSID': 'line', 'id': None})
            LINE_SEQ = "%03d" % (int(pline.get({'BOTSID': 'line', 'seq': None})),)
            LINE_PRODUCT = pline.get({'BOTSID': 'line', 'product': None})
            LINE_PRODUCT_SUPPLIER = pline.get({'BOTSID': 'line', 'product_supplier_sku': None})
            LINE_QTY = float(pline.get({'BOTSID': 'line', 'product_qty': None}) or 0.0)
            LINE_PRICE_UNIT = float(pline.get({'BOTSID': 'line', 'price_unit': None}) or 0.0)
            LINE_CURRENCY = pline.get({'BOTSID': 'line', 'price_currency': None})
            LINE_KEY = (LINE_PRODUCT, LINE_PRODUCT_SUPPLIER, LINE_PRICE_UNIT, LINE_CURRENCY)
            lines[LINE_KEY] = lines.get(LINE_KEY,0) + LINE_QTY

        for (LINE_PRODUCT, LINE_PRODUCT_SUPPLIER, LINE_PRICE_UNIT, LINE_CURRENCY), LINE_QTY in lines.iteritems():
            # ORDER LINES
            ORD_ITEMS += LINE_QTY
            ORD_LINES += 1
            ORD_TOTAL += LINE_PRICE_UNIT * LINE_QTY
            ORD_CURRENCY = ORD_CURRENCY or LINE_CURRENCY
            if LINE_CURRENCY != ORD_CURRENCY:
                raise NotImplementedError('Unable to handle order with multiple currencies')

            order_line_out = order_out.putloop({'BOTSID': 'po'}, {'BOTSID':'items'}, {'BOTSID':'item'})
            order_line_out.put({'BOTSID':'item', 'productCode': LINE_PRODUCT})
            order_line_out.put({'BOTSID':'item', 'supplierSKU': LINE_PRODUCT_SUPPLIER})
            order_line_out.put({'BOTSID':'item', 'quantity': LINE_QTY})
            order_line_out.put({'BOTSID':'item', 'unitCost': LINE_PRICE_UNIT})
            order_line_out.put({'BOTSID':'item', 'totalCost': LINE_PRICE_UNIT * LINE_QTY})

        # ORDER - Main element
        order_out.put({'BOTSID':'po', 'purchaseOrderReference': ORD_ID})
        order_out.put({'BOTSID':'po', 'purchaseOrderType': ORD_TYPE})
        order_out.put({'BOTSID':'po', 'supplierCode': PART_CODE})
        #order_out.put({'BOTSID':'po', 'deliveryStockPoint': ''}) # No default
        #order_out.put({'BOTSID':'po', 'shipByDate': ''}) # No default
        order_out.put({'BOTSID':'po', 'dueDate': ORD_DELIVERY_DATE})
        order_out.put({'BOTSID':'po', 'status': 'OPEN'})
        order_out.put({'BOTSID':'po', 'lineCount': ORD_LINES})
        order_out.put({'BOTSID':'po', 'pieceCount': ORD_ITEMS})
        order_out.put({'BOTSID':'po', 'itemTotalCost': ORD_TOTAL})
        order_out.put({'BOTSID':'po', 'supplierCurrency': ORD_CURRENCY})
        #order_out.put({'BOTSID':'po', 'supplierTerms': ''}) # No default
        #order_out.put({'BOTSID':'po', 'shipmentTerms': ''}) # FIXME: Incoterm - POs do not allow an incoterm to be specified, blank for now
        order_out.put({'BOTSID':'po', 'settlementDays': 60})
        #order_out.put({'BOTSID':'po', 'externalDocumentRef1': ''}) # No default
        #order_out.put({'BOTSID':'po', 'externalDocumentRef2': ''}) # No default
        order_out.put({'BOTSID':'po', 'territory': PART_COUNTRY})
