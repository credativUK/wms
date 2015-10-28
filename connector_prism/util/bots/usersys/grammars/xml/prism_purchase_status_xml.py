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
        'indented': True,
        }

structure=    [
    {ID:'purchaseOrders',MIN:1,MAX:1,
        QUERIES:{
            'frompartner':  {'BOTSID':'orders','sender':None},
            'topartner':    {'BOTSID':'orders','receiver':None},
            },
        LEVEL:[
        {ID:'order',MIN:1,MAX:999,LEVEL:[
            {ID:'items',MIN:1,MAX:1,LEVEL:[
                {ID:'item',MIN:1,MAX:999,LEVEL:[
                    {ID:'actions',MIN:0,MAX:1,LEVEL:[
                        {ID:'action',MIN:1,MAX:999},
                    ]},
                ]},
            ]},
        ]},
    ]},
]

nextmessage = ({'BOTSID':'purchaseOrders'},{'BOTSID':'order'})

recorddefs = {
    'envelope':[
            ['BOTSID','M',255,'A'],
          ],
    'purchaseOrders':[
            ['BOTSID','M',255,'A'],
          ],
    'order':[
            ['BOTSID','M',255,'A'],
            ['suppliercode', 'M', 30, 'A'],
            ['internalPurchaseOrderRef', 'M', 30, 'A'],
            ['supplierCurrency', 'M', 3, 'A'],
            ['dueDate', 'M', 10, 'A'],
            ['lineCount', 'M', 5, 'I'],
            ['pieceCount', 'C', 10, 'I'],
            ['deliveryToWarehouse', 'C', 10, 'A'],
          ],
    'items':[
            ['BOTSID','M',255,'A'],
          ],
    'item':[
            ['BOTSID','M',255,'A'],
            ['sku', 'M', 30, 'A'],
          ],
    'actions':[
            ['BOTSID','M',255,'A'],
          ],
    'action':[
            ['BOTSID','M',255,'A'],
            ['type', 'M', 20, 'A'],
            ['qty', 'M', 10, 'I'],
            ['date', 'C', 19, 'A'],
          ],
     }
 
