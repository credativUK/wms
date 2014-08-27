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

from util import serialize_dsv_xml, get_datetime, get_dsv_lang
from collections import OrderedDict
import re

SCHEMA = 'usersys/mappings/json/dsv_warehouseentryorder_schema.xsd'

def main(inn,out):

    root = {}
    rec_counts = {}

    # == HEADER - WEO00R ==
    if True:
        ELEMENT = "WEO00R"
        SEGMENT = "00"
        rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

        HEAD_ID = inn.get({'BOTSID': 'picking'}, {'BOTSID': 'header', 'message_id': None})
        HEAD_DATE, HEAD_TIME = get_datetime(inn.get({'BOTSID': 'picking'}, {'BOTSID': 'header', 'date_msg': None}))
        HEAD_TYPE = inn.get({'BOTSID': 'picking'}, {'BOTSID': 'header', 'type': None})
        assert HEAD_TYPE == 'in', "Warehouse Entry Orders must have type 'in', not '%s'" % (HEAD_TYPE,)
        HEAD_TYPE = "943" # Warehouse Entry Order

        d = OrderedDict([
                ('Segment_Number', SEGMENT),
                ('Identification_Nbr', HEAD_ID or ''),
                ('Message_Date', HEAD_DATE or ''),
                ('Message_Time', HEAD_TIME or ''),
                ('Message_Type_Id', HEAD_TYPE),
            ])
        root.setdefault(ELEMENT, []).append(d)

    pinn = inn.getloop({'BOTSID': 'picking'}, {'BOTSID': 'pickings'})
    for pick in pinn:
        ORD_ID = pick.get({'BOTSID': 'pickings', 'id': None})
        assert ORD_ID, "Order ID must be present"
        ORD_ID = re.sub(r'[\\/_-]', r'', ORD_ID.upper())
        ORD_STATE = pick.get({'BOTSID': 'pickings', 'state': None})

        # == Cancelled Orders - WEO05R ==
        if ORD_STATE == 'delete':
            ELEMENT = "WEO05R"
            SEGMENT = "05"
            rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

            d = OrderedDict([
                ('Segment_Number', SEGMENT),
                ('Order_Reference', ORD_ID),
            ])
            root.setdefault(ELEMENT, []).append(d)

        # == New Orders - WEO10R ==
        elif ORD_STATE == 'new':
            ELEMENT = "WEO10R"
            SEGMENT = "10"
            rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

            ORD_REMARK = pick.get({'BOTSID': 'pickings', 'desc': None})
            ORD_DELIVERY_DATE, dummy = get_datetime(pick.get({'BOTSID': 'pickings', 'date': None}) + ' 00:00:00.00000')

            ord_root = OrderedDict([
                ('Segment_Number', SEGMENT),
                ('Order_Type', 'I'), # Incoming
                ('Indicator_Transport', 'N'),
                ('Order_Reference', ORD_ID),
                ('Indicator_Labelling', 'N'),
                ('Indicator_contact_cl', 'N'),
                ('Order_Category', 'N'), # N = New
                ('Date_expected', ORD_DELIVERY_DATE),
                ('Remark', ORD_REMARK),
            ])
            root.setdefault(ELEMENT, []).append(ord_root)

            # == Order Remarks - WEO20R ==
            if ORD_REMARK:
                ELEMENT = "WEO20R"
                SEGMENT = "20"
                rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

                d = OrderedDict([
                    ('Segment_Number', SEGMENT),
                    ('Order_Remark', ORD_REMARK),
                    ('Order_Remark_Qual', 'G'), # General note (not for box label)
                ])
                ord_root.setdefault(ELEMENT, []).append(d)

            # == Order Party - WEO30R ==
            ELEMENT = "WEO30R"
            SEGMENT = "30"
            rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

            PART_ID = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'id': None})
            PART_EMAIL = pick.get({'BOTSID': 'pickings'}, {'BOTSID': 'partner', 'email': None})

            party_root = OrderedDict([
                ('Segment_Number', SEGMENT),
                ('Order_Party_Qual', 'CO'), # Consignor - Party sending goods
                ('Party_External_Ref', PART_ID),
            ])
            ord_root.setdefault(ELEMENT, []).append(party_root)

            # == Order Party Address - WEO32R ==
            ELEMENT = "WEO32R"
            SEGMENT = "32"
            rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

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

            d = OrderedDict([
                ('Segment_Number', SEGMENT),
                ('Company_Name_1', PART_NAME),
                ('Address_3', PART_STREET2),
                ('Postal_Code', PART_ZIP),
                ('Place_Name', PART_CITY),
                ('Country_Code', PART_COUNTRY),
                ('Language_code', get_dsv_lang(PART_LANG)),
                ('Telephone_Number', PART_PHONE),
                ('Telefax_Number', PART_FAX),
                ('VAT-number', PART_VAT),
                ('Address_2', PART_STREET1),
                ('Address_4', PART_STATE),
            ])
            party_root.setdefault(ELEMENT, []).append(d)

            plines = pick.getloop({'BOTSID': 'pickings'}, {'BOTSID': 'line'})
            for pline in plines:
                # == Order Line - WEO40R ==
                ELEMENT = "WEO40R"
                SEGMENT = "40"
                rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

                LINE_ID = pline.get({'BOTSID': 'line', 'id': None})
                LINE_SEQ = "%03d" % (int(pline.get({'BOTSID': 'line', 'seq': None})),)
                LINE_PRODUCT = pline.get({'BOTSID': 'line', 'product': None}).upper()
                LINE_TYPE = '*FIRST'
                LINE_QTY = pline.get({'BOTSID': 'line', 'product_qty': None})
                LINE_DESC = pline.get({'BOTSID': 'line', 'desc': None})
                LINE_VOLUME_NET = pline.get({'BOTSID': 'line', 'volume_net': None})
                LINE_WEIGHT = pline.get({'BOTSID': 'line', 'weight': None})
                LINE_WEIGHT_NET = pline.get({'BOTSID': 'line', 'weight_net': None})
                LINE_PRICE_UNIT = pline.get({'BOTSID': 'line', 'price_unit': None})
                LINE_CURRENCY = pline.get({'BOTSID': 'line', 'price_currency': None})
                LINE_CUSTOMS_FROM = pline.get({'BOTSID': 'line', 'customs_free_from': None})
                LINE_CUSTOMS_FROM = (LINE_CUSTOMS_FROM in ("1", "True", None) and 'FR') or 'T1'

                line_root = OrderedDict([
                    ('Segment_Number', SEGMENT),
                    ('Orderline_ID', LINE_SEQ),
                    ('SKU_Reference', LINE_PRODUCT),
                    ('Customs_Status_from', LINE_CUSTOMS_FROM),
                    ('Currency_customs_val', LINE_CURRENCY),
                    ('Type_of_package', LINE_TYPE),
                    ('Measure_unit_specifier', 'PCE'), # FIXME: We only support units UoM currently
                    ('Number_of_packages', LINE_QTY),
                    ('Number_of_units_measure_unit_specifier', LINE_QTY),
                    ('Number_of_units_measure_unit_specifier_per_type_of_package', 1), # FIXME: We only support units UoM currently
                    ('Orderline_remarks', LINE_DESC),
                    ('Net_volume_per_unit_measure_unit_specifier', LINE_VOLUME_NET),
                ])
                ord_root.setdefault(ELEMENT, []).append(line_root)

                # == Order Line Customs Value - WEO48R ==
                ELEMENT = "WEO48R"
                SEGMENT = "48"
                rec_counts[SEGMENT] = rec_counts.setdefault(SEGMENT, 0) + 1

                d = OrderedDict([
                    ('Segment_Number', SEGMENT),
                    ('Customs_value_qual', '001'), # Goods value
                    ('Customs_value', "%015.02f" % (float(LINE_PRICE_UNIT) * float(LINE_QTY)),),
                    ('Positive-sign', 'Y'),
                ])
                line_root.setdefault(ELEMENT, []).append(d)

        # Catch all
        else:
            raise NotImplementedError('Unable to handle order with state %s' % (ORD_STATE,))

    # == FOOTER - WEO99R ==
    rec_counts['99'] = len(rec_counts.keys())
    for FOOT_REC_TYPE, FOOT_REC_COUNT in rec_counts.iteritems():
        ELEMENT = "WEO99R"
        SEGMENT = "99"

        d = OrderedDict([
                ('Segment_Number', SEGMENT),
                ('RecordType', FOOT_REC_TYPE),
                ('Total_Nbrs_of_Rec', FOOT_REC_COUNT),
        ])
        root.setdefault(ELEMENT, []).append(d)

    root = OrderedDict(sorted(root.items(), key=lambda t: t[0]))
    document = OrderedDict([('WEO', root)])
    data = serialize_dsv_xml(document, SCHEMA)

    out.root = data
    return
