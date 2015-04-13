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
from util import get_datetime

def main(inn,out):

    pinn = inn.getloop({'BOTSID': 'picking'}, {'BOTSID': 'pickings'})
    main_out = out.putloop({'BOTSID': 'orders'})
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

        ORD_REMARK = pick.get({'BOTSID': 'pickings', 'desc': None})
        ORD_DELIVERY_DATE, dummy = get_datetime(pick.get({'BOTSID': 'pickings', 'date': None}) + ' 00:00:00.00000')
        ORDER_ATTRS = {}
        ORDER_PAYMENTS = [] # FIXME: We are not currently receiving payment details

        # == PARTNER ==

        PART_ID = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'id': None})
        PART_EMAIL = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'email': None})
        PART_NAME = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'name': None}) or ''
        PART_STREET1 = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'street1': None}) or ''
        PART_STREET2 = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'street2': None}) or ''
        PART_CITY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'city': None}) or ''
        PART_ZIP = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'zip': None}) or ''
        PART_COUNTRY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'country': None}) or ''
        PART_STATE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'state': None}) or ''
        PART_PHONE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'phone': None}) or ''
        PART_FAX = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'fax': None}) or ''
        PART_LANG = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'language': None}) or ''
        PART_VAT = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'vat': None}) or ''

        # == BILLING ==

        PART_BILL_ID = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'id': None})
        PART_BILL_EMAIL = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'email': None})
        PART_BILL_NAME = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'name': None}) or ''
        PART_BILL_STREET1 = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'street1': None}) or ''
        PART_BILL_STREET2 = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'street2': None}) or ''
        PART_BILL_CITY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'city': None}) or ''
        PART_BILL_ZIP = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'zip': None}) or ''
        PART_BILL_COUNTRY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'country': None}) or ''
        PART_BILL_STATE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'state': None}) or ''
        PART_BILL_PHONE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'phone': None}) or ''
        PART_BILL_FAX = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'fax': None}) or ''
        PART_BILL_LANG = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'language': None}) or ''
        PART_BILL_VAT = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'vat': None}) or ''

        order_out = main_out.putloop({'BOTSID': 'orders'}, {'BOTSID':'order'})

        # == LINES ==

        ORD_ITEMS = 0
        ORD_TOTAL = 0.0
        ORD_CURRENCY = None
        plines = pick.getloop({'BOTSID': 'pickings'}, {'BOTSID': 'line'})
        for pline in plines:
            LINE_ID = pline.get({'BOTSID': 'line', 'id': None})
            LINE_SEQ = "%03d" % (int(pline.get({'BOTSID': 'line', 'seq': None})),)
            LINE_PRODUCT = pline.get({'BOTSID': 'line', 'product': None}).upper()
            LINE_TYPE = '*FIRST'
            LINE_QTY = float(pline.get({'BOTSID': 'line', 'product_qty': None}) or 0.0)
            LINE_DESC = pline.get({'BOTSID': 'line', 'desc': None})
            LINE_VOLUME_NET = pline.get({'BOTSID': 'line', 'volume_net': None})
            LINE_WEIGHT = pline.get({'BOTSID': 'line', 'weight': None})
            LINE_WEIGHT_NET = pline.get({'BOTSID': 'line', 'weight_net': None})
            LINE_PRICE_UNIT = float(pline.get({'BOTSID': 'line', 'price_unit': None}) or 0.0)
            LINE_CURRENCY = pline.get({'BOTSID': 'line', 'price_currency': None})

            # ORDER LINES
            itr = 0
            for dummy in xrange(int(LINE_QTY or 0)): # FIXME: Shouldn't there be a qty field here? or just one entry per unit qty?
                itr += 1
                LINE_QTY = 1.0
                ORD_ITEMS += LINE_QTY
                ORD_TOTAL += LINE_PRICE_UNIT
                ORD_CURRENCY = ORD_CURRENCY or LINE_CURRENCY
                if LINE_CURRENCY != ORD_CURRENCY:
                    raise NotImplementedError('Unable to handle order with multiple currencies')
                LINE_ATTRS = {
                    'uniqueRecordID': "%s_%s" % (LINE_ID, itr), # FIXME: This is a unique ID per unit item, other system would not know this ID for mapping.
                }

                order_line_out = order_out.putloop({'BOTSID': 'order'}, {'BOTSID':'items'}, {'BOTSID':'item'})
                #order_line_out.put({'BOTSID':'item', 'postageProductType': ''}) # FIXME: What is this?
                order_line_out.put({'BOTSID':'item', 'productCode': LINE_PRODUCT})
                order_line_out.put({'BOTSID':'item', 'unitPrice': LINE_PRICE_UNIT})
                order_line_out.put({'BOTSID':'item', 'salesPrice': LINE_PRICE_UNIT * LINE_QTY})
                order_line_out.put({'BOTSID':'item', 'paidPrice': LINE_PRICE_UNIT * LINE_QTY})
                #order_line_out.put({'BOTSID':'item', 'tax': 0.00})
                #order_line_out.put({'BOTSID':'item', 'taxIncluded': 0.00})
                #order_line_out.put({'BOTSID':'item', 'taxRate': 0.00})

                for ATTR_NAME, ATTR_VALUE in LINE_ATTRS.iteritems():
                    order_line_attr = order_line_out.putloop({'BOTSID': 'item'}, {'BOTSID':'attributes'}, {'BOTSID':'attribute'})
                    order_line_attr.put({'BOTSID':'attribute', 'name': ATTR_NAME})
                    order_line_attr.put({'BOTSID':'attribute', 'value': ATTR_VALUE})

        # ORDER - Main element
        #order_out.put({'BOTSID':'order', 'orderType': 'B2C'}) # Default B2C
        #order_out.put({'BOTSID':'order', 'channel': 'WEB'}) # Default WEB
        #order_out.put({'BOTSID':'order', 'subChannel': ''}) # No Default
        order_out.put({'BOTSID':'order', 'currency': ORD_CURRENCY or 'GBP'})
        order_out.put({'BOTSID':'order', 'sourceCode': ''.join([x[:1] for x in PART_NAME.split(' ')])}) # Initials from partner name
        order_out.put({'BOTSID':'order', 'orderDate': ORD_DELIVERY_DATE})
        order_out.put({'BOTSID':'order', 'orderNumber': ORD_ID})
        #order_out.put({'BOTSID':'order', 'externalDocumentRef1': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'externalDocumentRef2': ''}) # No Default
        order_out.put({'BOTSID':'order', 'itemsCount': ORD_ITEMS})
        order_out.put({'BOTSID':'order', 'itemsValue': ORD_TOTAL})
        order_out.put({'BOTSID':'order', 'territory': PART_COUNTRY or 'GB'})
        #order_out.put({'BOTSID':'order', 'basicPostageRate': 0.00}) # Default 0.00
        #order_out.put({'BOTSID':'order', 'preferredCarrier': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'preferreCarrierService': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'carrierPremium': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'expressDelivery': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'expressPremium': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'giftOrder': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'giftWrap': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'giftMessage': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'giftWrapPremium': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'holdToComplete': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'tax': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'taxRegion': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'taxIncluded': ''}) # No Default
        order_out.put({'BOTSID':'order', 'deliveryInstructions': ORD_REMARK})

        # ATTRIBUTE elements
        for ATTR_NAME, ATTR_VALUE in ORDER_ATTRS.iteritems():
            order_attr = order_out.putloop({'BOTSID': 'order'}, {'BOTSID':'attributes'}, {'BOTSID':'attribute'})
            order_attr.put({'BOTSID':'attribute', 'name': ATTR_NAME})
            order_attr.put({'BOTSID':'attribute', 'value': ATTR_VALUE})

        # PARTNER elements
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'title': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'forename': ' '.join(PART_NAME.split(' ')[:1])}) # Take first name
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'surname': ' '.join(PART_NAME.split(' ')[1:])}) # Take all other names
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'jobTitle': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'company': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'address1': PART_STREET1})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'address2': PART_STREET2})
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'address3': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'addressType': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'city': PART_CITY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'region': PART_STATE})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'postCode': PART_ZIP})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'countryCode': PART_COUNTRY})
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'clientMarketingOk': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'externalMarketingOk': ''}) # No Default

        if PART_PHONE:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'number': PART_PHONE})
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'numberType': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'clientContactOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'clientMarketingOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'externalMarketingOk': ''}) # No Default

        if PART_EMAIL:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'displayName': PART_NAME})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'email': PART_EMAIL})
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'clientContactOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'clientMarketingOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'externalMarketingOk': ''}) # No Default

        # BILLING elements
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'title': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'forename': ' '.join(PART_BILL_NAME.split(' ')[:1])}) # Take first name
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'surname': ' '.join(PART_BILL_NAME.split(' ')[1:])}) # Take all other names
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'jobTitle': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'company': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'address1': PART_BILL_STREET1})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'address2': PART_BILL_STREET2})
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'address3': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'addressType': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'city': PART_BILL_CITY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'region': PART_BILL_STATE})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'postCode': PART_BILL_ZIP})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'countryCode': PART_BILL_COUNTRY})
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'clientMarketingOk': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'externalMarketingOk': ''}) # No Default

        if PART_BILL_PHONE:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'number': PART_BILL_PHONE})
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'numberType': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'clientContactOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'clientMarketingOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'externalMarketingOk': ''}) # No Default

        if PART_BILL_EMAIL:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'displayName': PART_BILL_NAME})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'email': PART_BILL_EMAIL})
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'clientContactOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'clientMarketingOk': ''}) # No Default
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'externalMarketingOk': ''}) # No Default

        # PAYMENTs elements
        for PAY_TYPE, PAY_CUR, PAY_VALUE in ORDER_PAYMENTS:
            order_attr = order_out.putloop({'BOTSID': 'order'}, {'BOTSID':'payments'}, {'BOTSID':'payment'})
            order_attr.put({'BOTSID':'payments', 'payType': PAY_TYPE})
            order_attr.put({'BOTSID':'payments', 'currency': PAY_CUR})
            order_attr.put({'BOTSID':'payments', 'paymentValue': PAY_VALUE})
