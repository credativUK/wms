from bots.botsconfig import *

syntax = { 
        'indented':True,
        }

structure = [
    {ID:'message',MIN:1,MAX:1,
    QUERIES:{
        'frompartner':  {'BOTSID':'message','sender':None},
        'topartner':    {'BOTSID':'message','receiver':None},
        'testindicator':{'BOTSID':'message','testindicator':None},
        },
    LEVEL:[
        {ID:'partys',MIN:0,MAX:1,LEVEL:[
            {ID:'party',MIN:1,MAX:99},
            ]},
        {ID:'lines',MIN:0,MAX:1,LEVEL:[
            {ID:'line',MIN:1,MAX:99999},
            ]},
        ]},
    ]

recorddefs = {
    'message':[
            ['BOTSID','M',255,'A'],
            ['sender', 'M', 35, 'AN'],
            ['receiver', 'M', 35, 'AN'],
            ['testindicator', 'C', 3, 'AN'],
            ['docnum', 'M', 22, 'AN'],
            ['docdtm', 'C', 35, 'AN'],
            ['cancel_after_date', 'C', 35, 'AN'],
            ['requested_ship_date', 'C', 35, 'AN'],
          ],
    'partys':[
            ['BOTSID','M',255,'A'],
          ],
    'party':[
            ['BOTSID','M',255,'A'],
            ['name1', 'C', 35, 'AN'],
            ['name2', 'C', 35, 'AN'],
            ['address1', 'C', 35, 'AN'],
            ['address2', 'C', 35, 'AN'],
            ['city', 'C', 20, 'AN'],
            ['pcode', 'C', 15, 'AN'],
            ['state', 'C', 2, 'AN'],
            ['country', 'C', 3, 'AN'],
          ],
    'lines':[
            ['BOTSID','M',255,'A'],
          ],
    'line':[
            ['BOTSID','M',255,'A'],
            ['linenum', 'C', 6, 'AN'],
            ['ordqua', 'C', 9, 'R'],
            ['price', 'C', 17, 'R'],
            ['product_sku', 'C', 40, 'AN'],
          ],
    'totals':[
            ['BOTSID','M',255,'A'],
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
 
