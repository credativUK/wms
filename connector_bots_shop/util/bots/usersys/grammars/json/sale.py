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

from bots.botsconfig import *

syntax = { 
        'indented':True,
        }

structure = [
{ID:'sale',MIN:1,MAX:1,
    QUERIES:{
        'frompartner':  ({'BOTSID':'sale'},{'BOTSID':'header','partner_from':None}),
        'topartner':    ({'BOTSID':'sale'},{'BOTSID':'header','partner_to':None}),
        'reference':    ({'BOTSID':'sale'},{'BOTSID':'header','message_id':None}),
        'testindicator':({'BOTSID':'sale'},{'BOTSID':'header','test':None})},
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'sales',MIN:0,MAX:999999,LEVEL:[
                {ID:'partner',MIN:0,MAX:99},
                {ID:'line',MIN:0,MAX:999999},
                {ID:'total',MIN:0,MAX:999999},
            ]},
        ]},
    ]

recorddefs = {
    'sale':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID','M',255,'A'],
            ['type','C',64,'A'],
            ['state','C',64,'A'],
            ['partner_to', 'C', 20, 'AN'],
            ['partner_from', 'C', 64, 'AN'],
            ['message_id', 'C', 64, 'AN'],
            ['test', 'C', 64, 'AN'],
            ['date_msg', 'C', 64, 'AN'],
            ['docnum', 'C', 64, 'AN'],
          ],
    'sales':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['name', 'C', 64, 'AN'],
            ['order', 'C', 64, 'AN'],
            ['order_date', 'C', 64, 'AN'],
            ['desc', 'C', 64, 'AN'],
            ['ship_date', 'C', 64, 'AN'],
            ['client_order_ref', 'C', 64, 'AN'],
            ['currency', 'C', 3, 'AN'],
            ['partner_name', 'C', 1000, 'AN'],
            ['partner_email', 'C', 1000, 'AN'],
          ],
    'partner':[
            ['BOTSID','M',255,'A'],
            ['type', 'C', 64, 'AN'],
            ['name1', 'C', 64, 'AN'],
            ['name2', 'C', 64, 'AN'],
            ['address1', 'C', 64, 'AN'],
            ['address2', 'C', 64, 'AN'],
            ['city', 'C', 64, 'AN'],
            ['zip', 'C', 15, 'AN'],
            ['state', 'C', 2, 'AN'],
            ['country', 'C', 3, 'AN'],
          ],
    'line':[
            ['BOTSID','M',255,'A'],
            ['seq', 'C', 6, 'AN'],
            ['qty', 'C', 9, 'R'],
            ['price', 'C', 17, 'R'],
            ['product_sku', 'C', 40, 'AN'],
          ],
    'total':[
            ['BOTSID','M',255,'A'],
            ['line_item_total', 'C', 18, 'R'],
            ['transaction_fee', 'C', 18, 'R'],
            ['sales_tax', 'C', 18, 'R'],
            ['handling_charges', 'C', 18, 'R'],
            ['total_invoice_amount', 'C', 18, 'R'],
          ],
     }
 
