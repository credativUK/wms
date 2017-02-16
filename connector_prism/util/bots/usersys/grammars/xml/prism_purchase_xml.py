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
    {ID:'pos',MIN:1,MAX:1,
        QUERIES:{
            'frompartner':  {'BOTSID':'orders','sender':None},
            'topartner':    {'BOTSID':'orders','receiver':None},
            },
        LEVEL:[
        {ID:'po',MIN:1,MAX:999,LEVEL:[
            {ID:'items',MIN:1,MAX:1,LEVEL:[
                {ID:'item',MIN:1,MAX:999},
            ]},
        ]},
    ]},
]

recorddefs = {
    'envelope':[
            ['BOTSID','M',255,'A'],
          ],
    'pos':[
            ['BOTSID','M',255,'A'],
          ],
    'po':[
            ['BOTSID','M',255,'A'],
            ['purchaseOrderReference', 'M', 30, 'A'],
            ['purchaseOrderType', 'M', 10, 'A'],
            ['supplierCode', 'M', 10, 'A'],
            ['deliveryStockPoint', 'C', 10, 'A'],
            ['shipByDate', 'C', 10, 'D'],
            ['dueDate', 'M', 10, 'A'],
            ['status', 'M', 10, 'A'],
            ['lineCount', 'M', 11, 'N'],
            ['pieceCount', 'M', 11, 'N'],
            ['itemTotalCost', 'C', 11, 'R'],
            ['supplierCurrency', 'C', 3, 'A'],
            ['supplierTerms', 'C', 10, 'A'],
            ['shipmentTerms', 'C', 10, 'A'],
            ['settlementDays', 'C', 3, 'I'],
            ['externalDocumentRef1', 'C', 999, 'A'],
            ['externalDocumentRef2', 'C', 999, 'A'],
            ['territory', 'M', 2, 'A'],
          ],
    'items':[
            ['BOTSID','M',255,'A'],
          ],
    'item':[
            ['BOTSID','M',255,'A'],
            ['productCode', 'M', 45, 'A'],
            ['supplierSKU', 'M', 64, 'A'],
            ['quantity', 'M', 11, 'I'],
            ['unitCost', 'C', 11, 'R'],
            ['totalCost', 'C', 11, 'R'],
          ],
     }
 
