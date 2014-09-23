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

from util import parse_dsv_xml, simplify_dsv_xml, get_datetime, get_address

SCHEMA = 'usersys/mappings/raw/dsv_orderconf_schema.xsd'

def main(inn,out):
    data = parse_dsv_xml(inn.root, SCHEMA)
    data = simplify_dsv_xml(data)

    for BODY in data['WOC']:
        lout = out.putloop({'BOTSID':'orderconf'})

        rec_counts = {}

        # == HEADER - WOC00R ==
        for HEAD in BODY.get('WOC00R', []):
            rec_counts['00'] = rec_counts.setdefault('00', 0) + 1
            if rec_counts['00'] > 1:
                continue # We only want one record at most
            HEAD_ID = HEAD.get('Principal-ID')
            HEAD_ID2 = HEAD.get('File-ID')
            HEAD_DATE = HEAD.get('Message_date')
            HEAD_TIME = HEAD.get('Message_time')
            HEAD_DATETIME = get_datetime(HEAD_DATE, HEAD_TIME)
            HEAD_FROM = HEAD.get('Principal_off_code')
            HEAD_TO = None
            HEAD_TEST = HEAD.get('Test_indicator')

            HEAD_STATE = HEAD.get('Message_type')
            HEAD_TYPE = HEAD.get('Message_type-ID')

            out.ta_info['frompartner'] = HEAD_FROM
            out.ta_info['topartner'] = HEAD_TO
            out.ta_info['testindicator'] = (HEAD_TEST == '1')

            lout.put({'BOTSID':'orderconf'},{'BOTSID':'header', 'msg_id': HEAD_ID})
            lout.put({'BOTSID':'orderconf'},{'BOTSID':'header', 'msg_id2': HEAD_ID2})
            lout.put({'BOTSID':'orderconf'},{'BOTSID':'header', 'datetime': HEAD_DATETIME})
            lout.put({'BOTSID':'orderconf'},{'BOTSID':'header', 'state': HEAD_STATE})
            lout.put({'BOTSID':'orderconf'},{'BOTSID':'header', 'type': HEAD_TYPE})
            lout.put({'BOTSID':'orderconf'},{'BOTSID':'header', 'test': out.ta_info['testindicator']})

        # == ORDER - WOC50R ==
        for ORD in BODY.get('WOC50R', []):
            rec_counts['50'] = rec_counts.setdefault('50', 0) + 1

            ORD_ID = ORD.get('Order_reference')
            ORD_NAME = ORD.get('Message_reference')
            ORD_DESC = ORD.get('Order_remarks')
            ORD_MANIFEST = ORD.get('Voyage_id')
            ORD_SHIP_DATE = get_datetime(ORD.get('Shipped_on_this_date'), '0000')
            ORD_DELIVERY_DATE = ORD.get('Delivery_date')
            ORD_DELIVERY_DATE_TYPE = {
                'O': 'ondate',
                'D': 'fromdate',
                }.get(ORD.get('Code_delivery_date', 'F'))
            ORD_TYPE = {
                'I': 'in',
                'O': 'out',
                'C': 'customs',
                'T': 'skuchange',
                'X': 'direct',
                }.get(ORD.get('Order_type'))
            ORD_REASON = {
                'B': 'backorder',
                'C': 'correction',
                'G': 'refuse',
                'H': 'return',
                'N': 'normal',
                'S': 'companytransfer',
                }.get(ORD.get('Order_category', 'N'))
            ORD_SERVICE_OUT = ORD.get('Ext_forw_service')
            ORD_CARRIER_CODE = ORD.get('Carrier_code')
            ORD_CONFIRMED = ORD.get('Indicator_Order_Executed')
            ORD_INVOICE_NAME = ORD.get('Invoice_number')
            ORD_INVOICE_CURRENCY = ORD.get('Currency_of_order')
            ORD_INVOICE_PAYTERM = ORD.get('Payment_term')
            ORD_B2_TYPE = {
                'B': 'B2B',
                'C': 'B2C',
                }.get(ORD.get('Sales_Channel'))

            oout = lout.putloop({'BOTSID': 'orderconf'}, {'BOTSID':'shipment'})
            oout.put({'BOTSID':'shipment', 'id': ORD_ID})
            oout.put({'BOTSID':'shipment', 'name': ORD_NAME})
            oout.put({'BOTSID':'shipment', 'desc': ORD_DESC})
            oout.put({'BOTSID':'shipment', 'manifest': ORD_MANIFEST})
            oout.put({'BOTSID':'shipment', 'date_ship': ORD_SHIP_DATE})
            oout.put({'BOTSID':'shipment', 'date_delivery': ORD_DELIVERY_DATE})
            oout.put({'BOTSID':'shipment', 'date_delivery_type': ORD_DELIVERY_DATE_TYPE})
            oout.put({'BOTSID':'shipment', 'type': ORD_TYPE})
            oout.put({'BOTSID':'shipment', 'reason': ORD_REASON})
            oout.put({'BOTSID':'shipment', 'service': ORD_SERVICE_OUT})
            oout.put({'BOTSID':'shipment', 'carrier': ORD_CARRIER_CODE})
            oout.put({'BOTSID':'shipment', 'confirmed': ORD_CONFIRMED})
            oout.put({'BOTSID':'shipment', 'buisness_type': ORD_B2_TYPE})
            oout.put({'BOTSID':'shipment'}, {'BOTSID':'invoice', 'name': ORD_INVOICE_NAME})
            oout.put({'BOTSID':'shipment'}, {'BOTSID':'invoice', 'currency': ORD_INVOICE_CURRENCY})
            oout.put({'BOTSID':'shipment'}, {'BOTSID':'invoice', 'payment_term': ORD_INVOICE_PAYTERM})

            # == ORDER REFERENCES - WOC51R ==
            for ORDID in ORD.get('WOC51R', []):
                rec_counts['51'] = rec_counts.setdefault('51', 0) + 1

                ORDID_ID = ORDID.get('Reference_number')
                ORDID_DESC = ORDID.get('Free_form_descr')
                ORDID_TYPE = {
                'EPF': 'invoice',
                'CON': 'consignment',
                'ABO': 'orig_ref',
                'PO': 'purchase_ref',
                'SI': 'shipping_ref',
                'SO': 'sale_ref',
                }.get(ORDID.get('Reference_qualifier'))
                ORDID_DATE = ORDID.get('Date')
                ORDID_TIME = ORDID.get('Time')
                ORDID_DATEIMTE = get_datetime(ORDID_DATE, ORDID_TIME)

                oidout = oout.putloop({'BOTSID': 'shipment'}, {'BOTSID':'references'})
                oidout.put({'BOTSID':'references', 'id': ORDID_ID})
                oidout.put({'BOTSID':'references', 'desc': ORDID_DESC})
                oidout.put({'BOTSID':'references', 'type': ORDID_TYPE})
                oidout.put({'BOTSID':'references', 'datetime': ORDID_DATEIMTE})

            # == ORDER VALUES - WOC52R ==
            for ORDVAL in ORD.get('WOC52R', []):
                rec_counts['52'] = rec_counts.setdefault('52', 0) + 1

                ORDVAL_CURRENCY = ORDVAL.get('Currency_code')
                ORDID_TOTAL = ORDVAL.get('Order_total')
                ORDVAL_TYPE = {
                'CTN': 'uoms',
                'PLT': 'pallets',
                'GRW': 'gross_grammes',
                'NTW': 'net_grammes',
                'MTQ': 'gross_cbm',
                'IN': 'invoice',
                'F01': 'proforma_exvat',
                }.get(ORDVAL.get('Qualifier'))

                ovalout = oout.putloop({'BOTSID': 'shipment'}, {'BOTSID':'values'})
                ovalout.put({'BOTSID':'values', 'type': ORDVAL_TYPE})
                ovalout.put({'BOTSID':'values', 'total': ORDID_TOTAL})
                ovalout.put({'BOTSID':'values', 'currency': ORDVAL_CURRENCY})

            # == PAL DETAILS - WOC54R ==
            for ORDLD in ORD.get('WOC54R', []):
                rec_counts['54'] = rec_counts.setdefault('54', 0) + 1
                # FIXME: Unused but count for validation

            # == BOX DETAILS - WOC56R ==
            for ORDLD in ORD.get('WOC56R', []):
                rec_counts['56'] = rec_counts.setdefault('56', 0) + 1
                # FIXME: Unused but count for validation

            # == SERVICE DETAILS - WOC59R ==
            for ORDLD in ORD.get('WOC59R', []):
                rec_counts['59'] = rec_counts.setdefault('59', 0) + 1
                # FIXME: Unused but count for validation

            # == PARTNER REFERENCE - WOC70R ==
            for PART in ORD.get('WOC70R', []):
                rec_counts['70'] = rec_counts.setdefault('70', 0) + 1
                for PART_ADD in PART.get('WOC72R', []):
                    rec_counts['72'] = rec_counts.setdefault('72', 0) + 1
                PART_ADD = PART.get('WOC72R', [{}])[0]

                PART_PARTNER_ID = PART.get('Party_external_reference')
                PART_ADD_NAME = PART_ADD.get('Company_name_1')
                PART_ADD_NAME2 = PART_ADD.get('Company_name_2')
                if PART_ADD_NAME2:
                    PART_ADD_NAME = PART_ADD_NAME + ", " + PART_ADD_NAME2
                PART_ADD_LINE1, PART_ADD_LINE2, PART_ADD_LINE3 = get_address(PART_ADD.get('House_number'), PART_ADD.get('House_number_extension'), PART_ADD.get('Address_1'), PART_ADD.get('Address_2'), PART_ADD.get('Address_3'), PART_ADD.get('Address_4'))
                PART_ADD_ZIP = PART_ADD.get('Postal_code')
                PART_ADD_STATE = PART_ADD.get('Place_name')
                PART_ADD_COUNTRY = PART_ADD.get('Country_code')
                PART_ADD_PHONE = PART_ADD.get('Telephone_number')
                PART_ADD_FAX = PART_ADD.get('Telefax_number')
                PART_ADD_VAT = PART_ADD.get('VAT-number')

                partout = oout.putloop({'BOTSID': 'shipment'}, {'BOTSID':'partner'})
                partout.put({'BOTSID':'partner', 'id': PART_PARTNER_ID})
                partout.put({'BOTSID':'partner', 'name': PART_ADD_NAME})
                partout.put({'BOTSID':'partner', 'street1': PART_ADD_LINE1})
                partout.put({'BOTSID':'partner', 'street2': PART_ADD_LINE2})
                partout.put({'BOTSID':'partner', 'city': PART_ADD_LINE3})
                partout.put({'BOTSID':'partner', 'state': PART_ADD_STATE})
                partout.put({'BOTSID':'partner', 'country': PART_ADD_COUNTRY})
                partout.put({'BOTSID':'partner', 'zip': PART_ADD_ZIP})
                partout.put({'BOTSID':'partner', 'phone': PART_ADD_PHONE})
                partout.put({'BOTSID':'partner', 'fax': PART_ADD_VAT})
                partout.put({'BOTSID':'partner', 'vat': PART_ADD_VAT})

            # == ORDER LINES - WOC80R ==
            for ORDL in ORD.get('WOC80R', []):
                rec_counts['80'] = rec_counts.setdefault('80', 0) + 1

                ORDL_DATE = HEAD.get('Date_executed')
                ORDL_TIME = HEAD.get('Time_executed')
                ORDL_PICK_DATE = HEAD.get('Picking_date')
                ORDL_PICK_TIME = HEAD.get('Picking_time')
                # take the one that is more precise with the picking time having precedence
                if ORDL_PICK_DATE and ORDL_PICK_TIME:
                    ORDL_DATETIME = get_datetime(ORDL_PICK_DATE, ORDL_PICK_TIME)
                elif ORDL_DATE and ORDL_TIME:
                    ORDL_DATETIME = get_datetime(ORDL_DATE, ORDL_TIME)
                else:
                    ORDL_DATETIME = get_datetime(ORDL_PICK_DATE, ORDL_PICK_TIME) or get_datetime(ORDL_DATE, ORDL_TIME)

                ORDL_ID = ORDL.get('Orderline_reference')
                ORDL_SEQ = ORDL.get('FL_order_line_nr')
                ORDL_TYPE = {
                'I': 'in',
                'O': 'out',
                }.get(ORDL.get('Orderline-type'))
                ORDL_PRODUCT = ORDL.get('SKU-reference')
                ORDL_QTY_UOM = ORDL.get('Quantity')
                ORDL_UOM = ORDL.get('Unit_of_Measure')
                ORDL_QTY_REAL = ORDL.get('Packages') or ORDL.get('Units_MUS')
                ORDL_QTY_EXPECTED = ORDL.get('Original_packages') or ORDL.get('Original_MUS')

                olout = oout.putloop({'BOTSID': 'shipment'}, {'BOTSID':'line'})
                olout.put({'BOTSID':'line', 'id': ORDL_ID})
                olout.put({'BOTSID':'line', 'seq': ORDL_SEQ})
                olout.put({'BOTSID':'line', 'type': ORDL_TYPE})
                olout.put({'BOTSID':'line', 'datetime': ORDL_DATETIME})
                olout.put({'BOTSID':'line', 'product': ORDL_PRODUCT})
                olout.put({'BOTSID':'line', 'uom_qty': ORDL_QTY_UOM})
                olout.put({'BOTSID':'line', 'uom': ORDL_UOM})
                olout.put({'BOTSID':'line', 'qty_real': ORDL_QTY_REAL})
                olout.put({'BOTSID':'line', 'qty_expected': ORDL_QTY_EXPECTED})

                # == ORDER LINE REFERENCES - WOC81R ==
                for ORDLID in ORDL.get('WOC81R', []):
                    rec_counts['81'] = rec_counts.setdefault('81', 0) + 1

                    ORDLID_ID = ORDLID.get('Reference_number')
                    ORDLID_DESC = ORDLID.get('Free_form_descr')
                    ORDLID_TYPE = {
                    'EPF': 'invoice',
                    'CON': 'consignment',
                    'ABO': 'orig_ref',
                    'PO': 'purchase_ref',
                    'SI': 'shipping_ref',
                    'SO': 'sale_ref',
                    'BAT': 'batch_seq',
                    'PBI': 'pick_batch',
                    'SO': 'pick_seq',
                    'SO': 'kit',
                    }.get(ORDLID.get('Reference_qualifier'))

                    oidout = olout.putloop({'BOTSID': 'line'}, {'BOTSID':'references'})
                    oidout.put({'BOTSID':'references', 'id': ORDLID_ID})
                    oidout.put({'BOTSID':'references', 'desc': ORDLID_DESC})
                    oidout.put({'BOTSID':'references', 'type': ORDLID_TYPE})

                # == ORDER LINE DETAILS - WOC83R ==
                for ORDLD in ORDL.get('WOC83R', []):
                    rec_counts['83'] = rec_counts.setdefault('83', 0) + 1
                    # FIXME: Unused but count for validation

                # == ORDER LINE DETAILS - WOC85R ==
                for ORDLD in ORDL.get('WOC85R', []):
                    rec_counts['85'] = rec_counts.setdefault('85', 0) + 1
                    # FIXME: Unused but count for validation


        for FOOT in BODY.get('WOC99R', []):
            rec_counts['99'] = rec_counts.setdefault('99', 0) + 1

        for FOOT in BODY.get('WOC99R', []):
            FOOT_REC_TYPE = FOOT.get('RecordType')
            FOOT_REC_COUNT = FOOT.get('Total_Nbrs_of_Rec')
            assert int(rec_counts.get(FOOT_REC_TYPE, 0)) == int(FOOT_REC_COUNT), "Expected %s of record %s, got %s" % (FOOT_REC_COUNT, FOOT_REC_TYPE, rec_counts.get(FOOT_REC_TYPE, 0))

    return
