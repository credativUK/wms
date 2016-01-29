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
    main_out = out.putloop({'BOTSID': 'orders'})
    for pick in pinn:
        # == MAIN ORDER ==
        ORD_ID = pick.get({'BOTSID': 'pickings', 'id': None})
        assert ORD_ID, "Order ID must be present"
        ORD_ID = re.sub(r'[\\/_-]', r'', ORD_ID.upper())
        out.ta_info['botskey'] = ORD_ID # Set the botskey to the last order ID
        ORD_STATE = pick.get({'BOTSID': 'pickings', 'state': None})

        if ORD_STATE == 'delete': # Ignore cancelled orders, not supported
            continue
        elif ORD_STATE != 'new': # Raise on other order state
            raise NotImplementedError('Unable to handle order with state %s' % (ORD_STATE,))

        ORD_ORDER = pick.get({'BOTSID': 'pickings', 'order': None})
        ORD_REMARK = pick.get({'BOTSID': 'pickings', 'desc': None})

        ORD_DELIVERY_DATE = pick.get({'BOTSID': 'pickings', 'order_date': None}) + ' 00:00:00'

        ORDER_ATTRS = {}

        # == PARTNER ==

        PART_ID = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'id': None})
        PART_EMAIL = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'email': None})
        PART_TITLE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'title': None}) or ''
        PART_JOBTITLE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'jobtitle': None}) or ''
        PART_COMPANY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'company': None}) or ''
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
        PART_BILL_TITLE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'title': None}) or ''
        PART_BILL_JOBTITLE = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'jobtitle': None}) or ''
        PART_BILL_COMPANY = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner_bill', 'company': None}) or ''
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

        # == ATTRIBUTES ==
        order_attrs = {}
        alines = pick.getloop({'BOTSID': 'pickings'}, {'BOTSID': 'attributes'})
        for aline in alines:
            order_attrs[aline.get({'BOTSID': 'attributes', 'key': None})] = aline.get({'BOTSID': 'attributes', 'value': None})

        # == LINES ==

        price_precision = 2
        percentage_precision = 4 # This is precission after coverting to a percentage

        ORD_ITEMS = 0
        ORD_TOTAL = 0.0
        ORD_CURRENCY = None
        plines = pick.getloop({'BOTSID': 'pickings'}, {'BOTSID': 'line'})
        for pline in plines:
            LINE_ID = pline.get({'BOTSID': 'line', 'id': None})
            LINE_SEQ = "%03d" % (int(pline.get({'BOTSID': 'line', 'seq': None})),)
            LINE_INTERNAL_ID = pline.get({'BOTSID': 'line', 'move_id': None})
            LINE_PRODUCT = pline.get({'BOTSID': 'line', 'product': None}).upper()
            LINE_TYPE = '*FIRST'
            LINE_CUSTOMS_TYPE = pline.get({'BOTSID': 'line', 'customs_commodity_code': None}) or '0'
            LINE_QTY = float(pline.get({'BOTSID': 'line', 'product_qty': None}) or 0.0)
            LINE_DESC = pline.get({'BOTSID': 'line', 'desc': None})
            LINE_VOLUME_NET = pline.get({'BOTSID': 'line', 'volume_net': None})
            LINE_WEIGHT = pline.get({'BOTSID': 'line', 'weight': None})
            LINE_WEIGHT_NET = pline.get({'BOTSID': 'line', 'weight_net': None})
            LINE_PRICE_UNIT = float(pline.get({'BOTSID': 'line', 'price_unit': None}) or 0.0)
            LINE_CURRENCY = pline.get({'BOTSID': 'line', 'price_currency': None})
            LINE_TOTAL_EX_VAT = pline.get({'BOTSID': 'line', 'price_total_ex_tax': None}) or 0.00
            LINE_TOTAL_INC_VAT = pline.get({'BOTSID': 'line', 'price_total_inc_tax': None}) or 0.00
            LINE_VAT = float(LINE_TOTAL_INC_VAT) - float(LINE_TOTAL_EX_VAT)
            LINE_VAT_RATE = float(pline.get({'BOTSID': 'line', 'tax_rate': None}))
            if LINE_VAT_RATE is None:
                LINE_VAT_RATE = float(LINE_TOTAL_EX_VAT) and 100 * (LINE_VAT / float(LINE_TOTAL_EX_VAT)) or 0.00

            # ORDER LINES
            itr = 0
            for dummy in xrange(int(LINE_QTY or 0)):
                itr += 1
                LINE_QTY = 1.0
                ORD_ITEMS += LINE_QTY
                ORD_TOTAL += LINE_PRICE_UNIT
                ORD_CURRENCY = ORD_CURRENCY or LINE_CURRENCY
                if LINE_CURRENCY != ORD_CURRENCY:
                    raise NotImplementedError('Unable to handle order with multiple currencies')
                LINE_UUID = "%s0M%s" % (itr, LINE_INTERNAL_ID)
                LINE_ATTRS = {
                    'uniqueRecordID': LINE_UUID,
                }

                order_line_out = order_out.putloop({'BOTSID': 'order'}, {'BOTSID':'items'}, {'BOTSID':'item'})
                order_line_out.put({'BOTSID':'item', 'postageProductType': LINE_CUSTOMS_TYPE})
                order_line_out.put({'BOTSID':'item', 'productCode': LINE_PRODUCT})
                order_line_out.put({'BOTSID':'item', 'unitPrice': round(0.0, price_precision)}) # LINE_PRICE_UNIT (0.0 as Prism doesn't expect this field to be set)
                order_line_out.put({'BOTSID':'item', 'salesPrice': round(0.0, price_precision)}) # LINE_PRICE_UNIT * LINE_QTY (0.0 as Prism doesn't expect this field to be set)
                order_line_out.put({'BOTSID':'item', 'paidPrice': round(LINE_PRICE_UNIT * LINE_QTY, price_precision)})
                order_line_out.put({'BOTSID':'item', 'tax': round(LINE_VAT, price_precision)})
                order_line_out.put({'BOTSID':'item', 'taxIncluded': 1})
                order_line_out.put({'BOTSID':'item', 'taxRate': round(LINE_VAT_RATE, percentage_precision)})

                for ATTR_NAME, ATTR_VALUE in LINE_ATTRS.iteritems():
                    order_line_attr = order_line_out.putloop({'BOTSID': 'item'}, {'BOTSID':'attributes'}, {'BOTSID':'attribute'})
                    order_line_attr.put({'BOTSID':'attribute', 'name': ATTR_NAME})
                    order_line_attr.put({'BOTSID':'attribute', 'value': ATTR_VALUE})

        ORDER_PAYMENTS = [('CARD', ORD_CURRENCY, ORD_TOTAL)] # Hardcoded for CARD for total order total

        ORDER_SUBCHANNEL = order_attrs.get('subChannel') or ''
        ORDER_POSTAGERATE = order_attrs.get('basicPostageRate') or 0.0
        ORDER_PREFCARRIER = order_attrs.get('preferredCarrier') or ''
        ORDER_PREFSERVICE = order_attrs.get('preferredCarrierService') or ''
        ORDER_EXPRESS = order_attrs.get('expressDelivery') # should be 0 or 1, not True or False.
        ORDER_GIFTMSG = order_attrs.get('giftMessage', '') or ''
        ORDER_CARRIERPREMIUM = order_attrs.get('carrier_premium') or 0.00
        ORDER_EXPRESSPREMIUM = order_attrs.get('express_premium') or 0.00

        # ORDER - Main element
        order_out.put({'BOTSID':'order', 'orderType': 'B2C'})
        order_out.put({'BOTSID':'order', 'channel': 'WEB'})
        order_out.put({'BOTSID':'order', 'subChannel': ORDER_SUBCHANNEL})
        order_out.put({'BOTSID':'order', 'currency': ORD_CURRENCY or 'GBP'})
        #order_out.put({'BOTSID':'order', 'sourceCode': ''.join([x[:1] for x in PART_NAME.split(' ')])}) # Initials from partner name
        order_out.put({'BOTSID':'order', 'orderDate': ORD_DELIVERY_DATE})
        order_out.put({'BOTSID':'order', 'orderNumber': ORD_ORDER})
        #order_out.put({'BOTSID':'order', 'externalDocumentRef1': ''}) # No Default
        #order_out.put({'BOTSID':'order', 'externalDocumentRef2': ''}) # No Default
        order_out.put({'BOTSID':'order', 'itemsCount': ORD_ITEMS})
        order_out.put({'BOTSID':'order', 'itemsValue': ORD_TOTAL})
        order_out.put({'BOTSID':'order', 'territory': PART_COUNTRY or 'GB'})
        order_out.put({'BOTSID':'order', 'basicPostageRate': ORDER_POSTAGERATE})
        order_out.put({'BOTSID':'order', 'preferredCarrier': ORDER_PREFCARRIER})
        order_out.put({'BOTSID':'order', 'preferredCarrierService': ORDER_PREFSERVICE})
        order_out.put({'BOTSID':'order', 'carrierPremium': ORDER_CARRIERPREMIUM})
        order_out.put({'BOTSID':'order', 'expressDelivery': ORDER_EXPRESS})
        order_out.put({'BOTSID':'order', 'expressPremium': ORDER_EXPRESSPREMIUM})
        order_out.put({'BOTSID':'order', 'giftOrder': 0})
        order_out.put({'BOTSID':'order', 'giftWrap': 0})
        order_out.put({'BOTSID':'order', 'giftMessage': ORDER_GIFTMSG})
        #order_out.put({'BOTSID':'order', 'giftWrapPremium': 0.00}) # No Default
        order_out.put({'BOTSID':'order', 'holdToComplete': 0})
        order_out.put({'BOTSID':'order', 'tax': 0.00}) # Prism doesn't use this value on the main order, only the order lines
        order_out.put({'BOTSID':'order', 'taxRegion': 'GB'})
        order_out.put({'BOTSID':'order', 'taxIncluded': 1})
        order_out.put({'BOTSID':'order', 'deliveryInstructions': ORD_REMARK})

        # ORDER_ATTRS
        if order_attrs.get('preferredCarrierService'):
            ORDER_ATTRS['despatchType'] = order_attrs.get('preferredCarrierService')
        if order_attrs.get('HDNCode'):
            ORDER_ATTRS['HDNCode'] = order_attrs.get('HDNCode')
        if order_attrs.get('cpCustomerNotify'):
            ORDER_ATTRS['cpCustomerNotify'] = order_attrs.get('cpCustomerNotify')

        # ATTRIBUTE elements
        for ATTR_NAME, ATTR_VALUE in ORDER_ATTRS.iteritems():
            order_attr = order_out.putloop({'BOTSID': 'order'}, {'BOTSID':'attributes'}, {'BOTSID':'attribute'})
            order_attr.put({'BOTSID':'attribute', 'name': ATTR_NAME})
            order_attr.put({'BOTSID':'attribute', 'value': ATTR_VALUE})

        # PARTNER elements
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'title': PART_TITLE}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'forename': ' '.join(PART_NAME.split(' ')[:1])}) # Take first name
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'surname': ' '.join(PART_NAME.split(' ')[1:])}) # Take all other names
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'jobTitle': PART_JOBTITLE})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'company': PART_COMPANY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'address1': PART_STREET1})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'address2': PART_STREET2})
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'address3': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'addressType': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'city': PART_CITY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'region': PART_STATE})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'postCode': PART_ZIP})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'countryCode': PART_COUNTRY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'clientMarketingOk': 0})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingAddress', 'externalMarketingOk': 0})

        if PART_PHONE:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'number': PART_PHONE})
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'numberType': ''}) # No Default
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'clientContactOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'clientMarketingOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingPhone1', 'externalMarketingOk': 0})

        if PART_EMAIL:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'displayName': PART_NAME})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'email': PART_EMAIL})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'clientContactOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'clientMarketingOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'shippingEmail', 'externalMarketingOk': 0})

        # BILLING elements
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'title': PART_BILL_TITLE}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'forename': ' '.join(PART_BILL_NAME.split(' ')[:1])}) # Take first name
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'surname': ' '.join(PART_BILL_NAME.split(' ')[1:])}) # Take all other names
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'jobTitle': PART_BILL_JOBTITLE})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'company': PART_BILL_COMPANY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'address1': PART_BILL_STREET1})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'address2': PART_BILL_STREET2})
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'address3': ''}) # No Default
        #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'addressType': ''}) # No Default
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'city': PART_BILL_CITY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'region': PART_BILL_STATE})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'postCode': PART_BILL_ZIP})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'countryCode': PART_BILL_COUNTRY})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'clientMarketingOk': 0})
        order_out.put({'BOTSID':'order'}, {'BOTSID':'billingAddress', 'externalMarketingOk': 0})

        if PART_BILL_PHONE:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'number': PART_BILL_PHONE})
            #order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'numberType': ''}) # No Default
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'clientContactOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'clientMarketingOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingPhone1', 'externalMarketingOk': 0})

        if PART_BILL_EMAIL:
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'displayName': PART_BILL_NAME})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'email': PART_BILL_EMAIL})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'clientContactOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'clientMarketingOk': 0})
            order_out.put({'BOTSID':'order'}, {'BOTSID':'billingEmail', 'externalMarketingOk': 0})

        # PAYMENTs elements
        for PAY_TYPE, PAY_CUR, PAY_VALUE in ORDER_PAYMENTS:
            order_attr = order_out.putloop({'BOTSID': 'order'}, {'BOTSID':'payments'}, {'BOTSID':'payment'})
            order_attr.put({'BOTSID':'payment', 'payType': PAY_TYPE})
            order_attr.put({'BOTSID':'payment', 'currency': PAY_CUR})
            order_attr.put({'BOTSID':'payment', 'paymentValue': PAY_VALUE})
