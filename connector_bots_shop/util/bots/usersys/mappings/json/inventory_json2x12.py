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

import bots.transform as transform

def main(inn,out):
    out.put({'BOTSID':'ST','ST01':'846','ST02':out.ta_info['reference'].zfill(4)})

    out.put({'BOTSID':'ST'},{'BOTSID':'BIA',
                             'BIA01':'08',  # Status
                             'BIA02':'MM',  # Manufacturer/Manufacturer Inventory
                             'BIA03': '000000', # Unused
                             'BIA04': transform.datemask(inn.get({'BOTSID': 'inventory'}, {'BOTSID': 'header', 'date_msg': None}),'CCYY-MM-DD HH:mm:ss','CCYYMMDD'),  # Date of transaction
                             'BIA05': transform.datemask(inn.get({'BOTSID': 'inventory'}, {'BOTSID': 'header', 'date_msg': None}),'CCYY-MM-DD HH:mm:ss','HHmmss'),  # Time of transaction
                             })

    pinn = inn.getloop({'BOTSID': 'inventory'}, {'BOTSID': 'products'})
    counter = 0
    for product in pinn:
        counter += 1
        pou = out.putloop({'BOTSID':'ST'},{'BOTSID':'LIN'})
        pou.put({'BOTSID':'LIN',
                             'LIN01':counter, # Unique within transaction
                             'LIN02':'SK', # Stock Keeping Unit (SKU)
                             'LIN03':product.get({'BOTSID': 'products', 'product_sku': None}), # Product ID
                             })
        pou.put({'BOTSID':'LIN'},{'BOTSID':'QTY',
                             'QTY01':'RJ', # Quantity Available On Shelf
                             'QTY02':product.get({'BOTSID': 'products', 'quantity': None}), # Quantity
                             'QTY03':'EA', # Each
                             })

    out.put({'BOTSID':'ST'},{'BOTSID':'CTT',
                             'CTT01':counter,
                             })
    out.put({'BOTSID':'ST'},{'BOTSID':'SE',
                             'SE01':out.getcount()+1, #SE01: bots counts the segments produced in the X12 message.
                             'SE02':out.ta_info['reference'].zfill(4),
                             })
