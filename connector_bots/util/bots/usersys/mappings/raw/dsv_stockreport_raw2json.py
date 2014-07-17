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

SCHEMA = 'usersys/mappings/raw/dsv_stockreport_schema.xsd'

def main(inn,out):
    data = parse_dsv_xml(inn.root, SCHEMA)
    data = simplify_dsv_xml(data)

    for BODY in data['SR']:
        lout = out.putloop({'BOTSID':'inventory'})

        rec_counts = {}

        # == HEADER - SR00R ==
        for HEAD in BODY.get('SR00R', []):
            rec_counts['00'] = rec_counts.setdefault('00', 0) + 1
            if rec_counts['00'] > 1:
                continue # We only want one record at most
            HEAD_ID = HEAD.get('Message_Identification')
            HEAD_DATE = HEAD.get('Message_date')
            HEAD_TIME = HEAD.get('Message_time')
            HEAD_DATETIME = get_datetime(HEAD_DATE, HEAD_TIME)
            HEAD_FROM = HEAD.get('Sender_Identification')
            HEAD_TO = None

            out.ta_info['frompartner'] = HEAD_FROM
            out.ta_info['topartner'] = HEAD_TO

            lout.put({'BOTSID':'inventory'},{'BOTSID':'header', 'msg_id': HEAD_ID})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'header', 'datetime': HEAD_DATETIME})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'header', 'partner_name': HEAD_FROM})

        # == WAREHOUSE REFERENCE - SR70R ==
        for WH in BODY.get('SR70R', []):
            rec_counts['70'] = rec_counts.setdefault('70', 0) + 1
            if rec_counts['70'] > 1:
                continue # We only want one record at most

            for WH_ADD in WH.get('SR72R', []):
                rec_counts['72'] = rec_counts.setdefault('72', 0) + 1

            WH_ADD = WH.get('SR72R', [{}])[0]

            WH_PARTNER_ID = WH.get('Party_external_reference')
            WH_ADD_NAME = WH_ADD.get('Company_name_1')
            WH_ADD_NAME2 = WH_ADD.get('Company_name_2')
            if WH_ADD_NAME2:
                WH_ADD_NAME = WH_ADD_NAME + ", " + WH_ADD_NAME2
            WH_ADD_LINE1, WH_ADD_LINE2, WH_ADD_LINE3 = get_address(WH_ADD.get('House_number'), WH_ADD.get('House_number_extension'), WH_ADD.get('Address_1'), WH_ADD.get('Address_2'), WH_ADD.get('Address_3'), WH_ADD.get('Address_4'))
            WH_ADD_ZIP = WH_ADD.get('Postal_code')
            WH_ADD_CITY = WH_ADD.get('Place_name')
            WH_ADD_COUNTRY = WH_ADD.get('Country_code')
            WH_ADD_PHONE = WH_ADD.get('Telephone_number')
            WH_ADD_FAX = WH_ADD.get('Telefax_number')
            WH_ADD_VAT = WH_ADD.get('VAT-number')

            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'id': WH_PARTNER_ID})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'name': WH_ADD_NAME})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'address1': WH_ADD_LINE1})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'address2': WH_ADD_LINE2})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'address3': WH_ADD_LINE3})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'city': WH_ADD_CITY})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'country': WH_ADD_COUNTRY})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'phone': WH_ADD_PHONE})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'fax': WH_ADD_FAX})
            lout.put({'BOTSID':'inventory'},{'BOTSID':'partner', 'vat': WH_ADD_VAT})

        # == STOCK LEVELS - SR8AR ==
        for SL in BODY.get('SR8AR', []):
            rec_counts['8A'] = rec_counts.setdefault('8A', 0) + 1
            SL_PRODUCT = SL.get('Lot_external_reference')
            SL_PRODUCT_ARTICLE = SL.get('Article_reference')
            SL_PRODUCT_CODE = SL.get('Product_code')
            SL_PRODUCT_CODE_TYPE = SL.get('Product_code_qualifier')
            SL_QTY_INCOMING = SL.get('Expected_in')
            SL_QTY_AVAILABLE = SL.get('Physical_stock_available')
            SL_QTY_OUTGOING = SL.get('Expected_out')
            SL_QTY_OUTGOING_AVAILABLE = SL.get('Reserved_sufficient')
            SL_QTY_OUTGOING_FUTURE = SL.get('Reserved_insufficient')
            SL_DATE = SL.get('Date_the_stock_was_determined')
            SL_TIME = SL.get('Time_the_stock_was_determined')
            SL_DATETIME = get_datetime(SL_DATE, SL_TIME)

            sout = lout.putloop({'BOTSID': 'inventory'}, {'BOTSID':'inventory_line'})
            sout.put({'BOTSID':'inventory_line', 'product': SL_PRODUCT})
            sout.put({'BOTSID':'inventory_line', 'product_article_no': SL_PRODUCT_ARTICLE})
            sout.put({'BOTSID':'inventory_line', 'product_other': SL_PRODUCT_CODE})
            sout.put({'BOTSID':'inventory_line', 'product_other_type': SL_PRODUCT_CODE_TYPE})
            sout.put({'BOTSID':'inventory_line', 'qty_incoming': SL_QTY_INCOMING})
            sout.put({'BOTSID':'inventory_line', 'qty_available': SL_QTY_AVAILABLE})
            sout.put({'BOTSID':'inventory_line', 'qty_outgoing': SL_QTY_OUTGOING})
            sout.put({'BOTSID':'inventory_line', 'qty_outgoing_available': SL_QTY_OUTGOING_AVAILABLE})
            sout.put({'BOTSID':'inventory_line', 'qty_outgoing_future': SL_QTY_OUTGOING_FUTURE})
            sout.put({'BOTSID':'inventory_line', 'datetime': SL_DATETIME})

        # == FOOTER - SR99R ==
        for FOOT in BODY.get('SR99R', []):
            rec_counts['99'] = rec_counts.setdefault('99', 0) + 1

        for FOOT in BODY.get('SR99R', []):
            FOOT_REC_TYPE = FOOT.get('RecordType')
            FOOT_REC_COUNT = FOOT.get('Total_Nbrs_of_Rec')
            assert int(rec_counts.get(FOOT_REC_TYPE, 0)) == int(FOOT_REC_COUNT), "Expected %s of record %s, got %s" % (FOOT_REC_COUNT, FOOT_REC_TYPE, rec_counts.get(FOOT_REC_TYPE, 0))

    return
