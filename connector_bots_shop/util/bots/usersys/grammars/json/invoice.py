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
    {ID:'invoice',MIN:1,MAX:1,
    QUERIES:{
        'frompartner':  ({'BOTSID':'invoice'},{'BOTSID':'header','partner_from':None}),
        'topartner':    ({'BOTSID':'invoice'},{'BOTSID':'header','partner_to':None}),
        'reference':    ({'BOTSID':'invoice'},{'BOTSID':'header','message_id':None}),
        'testindicator':({'BOTSID':'invoice'},{'BOTSID':'header','test':None}),
        },
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'invoices',MIN:0,MAX:999999,LEVEL:[
                {ID:'partner',MIN:0,MAX:99},
                {ID:'lines',MIN:0,MAX:999999},
            ]},
        ]},
    ]

recorddefs = {
    'invoice':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID', 'M', 64, 'AN'],
            ['state','C',64,'A'],
            ['partner_to', 'C', 20, 'AN'],
            ['partner_from', 'C', 64, 'AN'],
            ['message_id', 'C', 64, 'AN'],
            ['test', 'C', 64, 'AN'],
            ['date_msg', 'C', 64, 'AN'],
          ],
    'invoices':[
            ['BOTSID','M',255,'A'],
            ['id', 'C', 35, 'AN'],
            ['ref', 'C', 35, 'AN'],
            ['date', 'C', 35, 'AN'],
            ['sale', 'C', 35, 'AN'],
            ['sale_date', 'C', 35, 'AN'],
            ['currency', 'C', 3, 'AN'],
            ['total', 'C', 20, 'R'],
          ],
    'partner':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
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
    'lines':[
            ['BOTSID','M',255,'A'],
            ['id','C',64,'AN'],
            ['seq', 'C', 6, 'AN'],
            ['product_sku', 'C', 35, 'AN'],
            ['product_qty', 'C', 20, 'R'],
            ['desc', 'C', 70, 'AN'],
            ['total', 'C', 20, 'R'],
            ['unit_price', 'C', 20, 'R'],
          ],
     }
 
