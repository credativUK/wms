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
    {ID:'orders',MIN:1,MAX:1,
        QUERIES:{
            'frompartner':  {'BOTSID':'orders','sender':None},
            'topartner':    {'BOTSID':'orders','receiver':None},
            },
        LEVEL:[
        {ID:'order',MIN:1,MAX:999,LEVEL:[
            {ID:'attributes',MIN:0,MAX:1,LEVEL:[
                {ID:'attribute',MIN:0,MAX:999},
            ]},
            {ID:'billingAddress',MIN:1,MAX:1},
            {ID:'billingPhone1',MIN:0,MAX:1},
            {ID:'billingEmail',MIN:0,MAX:1},
            {ID:'shippingAddress',MIN:1,MAX:1},
            {ID:'shippingPhone1',MIN:0,MAX:1},
            {ID:'shippingEmail',MIN:0,MAX:1},
            {ID:'payments',MIN:0,MAX:1,LEVEL:[
                {ID:'payment',MIN:0,MAX:999},
            ]},
            {ID:'items',MIN:1,MAX:1,LEVEL:[
                {ID:'item',MIN:1,MAX:999,LEVEL:[
                    {ID:'attributes',MIN:0,MAX:1,LEVEL:[
                        {ID:'attribute',MIN:0,MAX:999},
                    ]},
                ]},
            ]},
        ]},
    ]},
]

recorddefs = {
    'envelope':[
            ['BOTSID','M',255,'A'],
          ],
    'message':[
            ['BOTSID','M',255,'A'],
          ],
    'orders':[
            ['BOTSID','M',255,'A'],
          ],
    'order':[
            ['BOTSID','M',255,'A'],
            ['orderType', 'C', 13, 'A'],
            ['channel', 'C', 9, 'A'],
            ['subChannel', 'C', 70, 'A'],
            ['currency', 'M', 3, 'A'],
            ['sourceCode', 'C', 10, 'A'],
            ['orderDate', 'M', 19, 'A'],
            ['orderNumber', 'M', 10, 'A'],
            ['externalDocumentRef1', 'C', 25, 'A'],
            ['externalDocumentRef2', 'C', 25, 'A'],
            ['itemsCount', 'M', 9, 'I'],
            ['itemsValue', 'M', 11, 'R'],
            ['territory', 'C', 2, 'A'],
            ['basicPostageRate', 'C', 11, 'R'],
            ['preferredCarrier', 'C', 50, 'A'],
            ['preferredCarrierService', 'C', 50, 'A'],
            ['carrierPremium', 'C', 11, 'R'],
            ['expressDelivery', 'C', 1, 'N'],
            ['expressPremium', 'C', 11, 'R'],
            ['giftOrder', 'C', 1, 'N'],
            ['giftWrap', 'C', 1, 'N'],
            ['giftMessage', 'C', 150, 'A'],
            ['giftWrapPremium', 'C', 11, 'R'],
            ['holdToComplete', 'C', 1, 'N'],
            ['tax', 'C', 5, 'R'],
            ['taxRegion', 'C', 2, 'A'],
            ['taxIncluded', 'C', 1, 'N'],
            ['deliveryInstructions', 'C', 50, 'A'],
          ],
    'attributes':[
            ['BOTSID','M',255,'A'],
          ],
    'attribute':[
            ['BOTSID','M',255,'A'],
            ['name', 'M', 50, 'AN'],
            ['value', 'M', 99999, 'AN'],
          ],
    'billingAddress':[
            ['BOTSID','M',255,'A'],
            ['title', 'C', 10, 'A'],
            ['forename', 'M', 30, 'A'],
            ['surname', 'M', 30, 'A'],
            ['jobTitle', 'C', 50, 'A'],
            ['company', 'C', 60, 'A'],
            ['address1', 'M', 60, 'A'],
            ['address2', 'C', 60, 'A'],
            ['address3', 'C', 60, 'A'],
            ['addressType', 'C', 5, 'A'],
            ['city', 'M', 50, 'A'],
            ['region', 'C', 50, 'A'],
            ['postCode', 'C', 20, 'A'],
            ['countryCode', 'M', 2, 'A'],
            ['clientMarketingOk', 'C', 1, 'I'],
            ['externalMarketingOk', 'C', 1, 'I'],
          ],
    'billingPhone1':[
            ['BOTSID','M',255,'A'],
            ['number', 'M', 20, 'A'],
            ['numberType', 'C', 5, 'A'],
            ['clientContactOk', 'C', 1, 'I'],
            ['clientMarketingOk', 'C', 1, 'I'],
            ['externalMarketingOk', 'C', 1, 'I'],
          ],
    'billingEmail':[
            ['BOTSID','M',255,'A'],
            ['displayName', 'M', 50, 'A'],
            ['email', 'M', 50, 'A'],
            ['clientContactOk', 'C', 1, 'I'],
            ['clientMarketingOk', 'C', 1, 'I'],
            ['externalMarketingOk', 'C', 1, 'I'],
          ],
    'shippingAddress':[
            ['BOTSID','M',255,'A'],
            ['title', 'C', 10, 'A'],
            ['forename', 'M', 30, 'A'],
            ['surname', 'M', 30, 'A'],
            ['jobTitle', 'C', 50, 'A'],
            ['company', 'C', 60, 'A'],
            ['address1', 'M', 60, 'A'],
            ['address2', 'C', 60, 'A'],
            ['address3', 'C', 60, 'A'],
            ['addressType', 'C', 5, 'A'],
            ['city', 'M', 50, 'A'],
            ['region', 'C', 50, 'A'],
            ['postCode', 'C', 20, 'A'],
            ['countryCode', 'M', 2, 'A'],
            ['clientMarketingOk', 'C', 1, 'I'],
            ['externalMarketingOk', 'C', 1, 'I'],
          ],
    'shippingPhone1':[
            ['BOTSID','M',255,'A'],
            ['number', 'M', 20, 'A'],
            ['numberType', 'C', 5, 'A'],
            ['clientContactOk', 'C', 1, 'I'],
            ['clientMarketingOk', 'C', 1, 'I'],
            ['externalMarketingOk', 'C', 1, 'I'],
          ],
    'shippingEmail':[
            ['BOTSID','M',255,'A'],
            ['displayName', 'M', 50, 'A'],
            ['email', 'M', 50, 'A'],
            ['clientContactOk', 'C', 1, 'I'],
            ['clientMarketingOk', 'C', 1, 'I'],
            ['externalMarketingOk', 'C', 1, 'I'],
          ],
    'payments':[
            ['BOTSID','M',255,'A'],
          ],
    'payment':[
            ['BOTSID','M',255,'A'],
            ['payType', 'C', 20, 'A'],
            ['currency', 'C', 3, 'A'],
            ['paymentValue', 'M', 11, 'R'],
          ],
    'items':[
            ['BOTSID','M',255,'A'],
          ],
    'item':[
            ['BOTSID','M',255,'A'],
            ['postageProductType', 'M', 30, 'A'],
            ['productCode', 'M', 30, 'A'],
            ['unitPrice', 'C', 11, 'R'],
            ['salesPrice', 'C', 11, 'R'],
            ['paidPrice', 'M', 11, 'R'],
            ['tax', 'C', 11, 'R'],
            ['taxIncluded', 'C', 1, 'I'],
            ['taxRate', 'C', 7, 'R'],
          ],
     }
 
