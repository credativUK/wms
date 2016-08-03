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

from bots.botsconfig import *

syntax = { 
        'indented': True,
    }

structure = [
{ID:'picking',MIN:1,MAX:1,
    QUERIES:{
        'frompartner':  ({'BOTSID':'picking'},{'BOTSID':'header','partner_from':None}),
        'topartner':    ({'BOTSID':'picking'},{'BOTSID':'header','partner_to':None}),
        'reference':    ({'BOTSID':'picking'},{'BOTSID':'header','message_id':None}),
        'testindicator':({'BOTSID':'picking'},{'BOTSID':'header','test':None})},
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'pickings',MIN:0,MAX:999999,LEVEL:[
                {ID:'partner',MIN:0,MAX:1},
                {ID:'partner_bill',MIN:0,MAX:1},
                {ID:'line',MIN:0,MAX:999999},
                {ID:'attributes',MIN:0,MAX:999999},
            ]},
        ]},
]

recorddefs = {
    'picking':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID', 'M', 64, 'AN'],
            ['type','C',64,'A'],
            ['state','C',64,'A'],
            ['partner_to', 'C', 20, 'AN'],
            ['partner_from', 'C', 64, 'AN'],
            ['message_id', 'C', 64, 'AN'],
            ['test', 'C', 64, 'AN'],
            ['date_msg', 'C', 64, 'AN'],
            ['docnum', 'C', 64, 'AN'],
          ],
    'pickings':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['name', 'C', 64, 'AN'],
            ['order', 'C', 64, 'AN'],
            ['order_date', 'C', 64, 'AN'],
            ['desc', 'C', 64, 'AN'],
            ['prio', 'C', 1, 'AN'],
            ['state', 'C', 64, 'AN'],
            ['type', 'C', 64, 'AN'],
            ['date', 'C', 64, 'AN'],
            ['crossdock', 'C', 1, 'N'],
            ['ship_date', 'C', 64, 'AN'],
            ['client_order_ref', 'C', 17, 'AN'],
            ['incoterm', 'C', 3, 'AN'],
            ['tracking_number', 'C', 64, 'AN'],
          ],
    'partner':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['code','C',64,'AN'],
            ['title', 'C', 64, 'AN'],
            ['jobtitle', 'C', 64, 'AN'],
            ['company', 'C', 64, 'AN'],
            ['name', 'C', 64, 'AN'],
            ['street1', 'C', 64, 'AN'],
            ['street2', 'C', 64, 'AN'],
            ['city', 'C', 64, 'AN'],
            ['zip', 'C', 64, 'AN'],
            ['country', 'C', 64, 'AN'],
            ['state', 'C', 64, 'AN'],
            ['phone', 'C', 64, 'AN'],
            ['fax', 'C', 64, 'AN'],
            ['email', 'C', 64, 'AN'],
            ['language', 'C', 64, 'AN'],
            ['vat', 'C', 64, 'AN'],
          ],
    'partner_bill':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['code','C',64,'AN'],
            ['title', 'C', 64, 'AN'],
            ['jobtitle', 'C', 64, 'AN'],
            ['company', 'C', 64, 'AN'],
            ['name', 'C', 64, 'AN'],
            ['street1', 'C', 64, 'AN'],
            ['street2', 'C', 64, 'AN'],
            ['city', 'C', 64, 'AN'],
            ['zip', 'C', 64, 'AN'],
            ['country', 'C', 64, 'AN'],
            ['state', 'C', 64, 'AN'],
            ['phone', 'C', 64, 'AN'],
            ['fax', 'C', 64, 'AN'],
            ['email', 'C', 64, 'AN'],
            ['language', 'C', 64, 'AN'],
            ['vat', 'C', 64, 'AN'],
          ],
    'line':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['seq', 'C', 64, 'AN'],
            ['move_id', 'C', 64, 'AN'],
            ['product', 'C', 64, 'AN'],
            ['product_supplier_sku', 'C', 64, 'AN'],
            ['product_sku', 'C', 64, 'AN'],
            ['product_qty', 'C', 64, 'AN'],
            ['ordered_qty', 'C', 64, 'AN'],
            ['uom', 'C', 64, 'AN'],
            ['product_uos_qty', 'C', 64, 'AN'],
            ['uos', 'C', 64, 'AN'],
            ['volume_net', 'C', 64, 'AN'],
            ['weight', 'C', 64, 'AN'],
            ['weight_net', 'C', 64, 'AN'],
            ['price_unit', 'C', 64, 'AN'],
            ['price_unit_ex_vat', 'C', 64, 'AN'],
            ['price_currency', 'C', 64, 'AN'],
            ['price_total_ex_tax', 'C', 64, 'AN'],
            ['price_total_inc_tax', 'C', 64, 'AN'],
            ['tax_rate', 'C', 64, 'AN'],
            ['desc', 'C', 64, 'AN'],
            ['customs_free_from', 'C', 64, 'AN'],
            ['customs_free_to', 'C', 64, 'AN'],
            ['customs_commodity_code', 'C', 64, 'AN'],
            ['bundle', 'C', 64, 'AN'],
          ],
    'attributes':[
            ['BOTSID', 'M', 64, 'AN'],
            ['key','C',128,'AN'],
            ['value', 'C', 128, 'AN'],
          ],
     }

