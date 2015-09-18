#mapping-script
from x12lib import get_art_num          #import x12 specifc helper function
import bots.transform as transform      #import div bots helper functions

def main(inn,out):
    #pick up some values from ISA envelope
    # Expected values for current implementation:
    #  * BEG02: NE: New Order
    #  * CUR02: USD: US Dollar
    #  * N101: BS: Bill and ship to
    #  * PO103: EA: each
    #  * PO105: PE: Price Per Each
    out.put({'BOTSID':'sale'},{'BOTSID':'header','partner_from':inn.ta_info['frompartner']})
    out.put({'BOTSID':'sale'},{'BOTSID':'header','partner_to':inn.ta_info['topartner']})
    out.put({'BOTSID':'sale'},{'BOTSID':'header','test':inn.ta_info['testindicator']})

    #pick up document number. is used in bots to give 'document-view'
    docnum = inn.get({'BOTSID':'ST'},{'BOTSID':'BEG','BEG03':None})
    out.put({'BOTSID':'sale'},{'BOTSID':'header','docnum':docnum})
    inn.ta_info['botskey']=docnum
    out.ta_info['botskey']=docnum

    order_date = inn.get({'BOTSID':'ST'},{'BOTSID':'BEG','BEG05':None})
    order_date = transform.datemask(order_date,'CCYYMMDD','CCYY-MM-DD')
    out.put({'BOTSID':'sale'},{'BOTSID':'header','date_msg':order_date}) # Sale order date

    order_number = inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'PO','REF02':None})
    order_currency = inn.get({'BOTSID':'ST'},{'BOTSID':'CUR','CUR02':None}) or 'USD'
    customer_email = inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'EM','REF02':None})
    customer_name = inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'NM','REF02':None})
    program_ref = inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'PID','REF02':None})

    # Only a single sale per message
    oout = out.putloop({'BOTSID': 'sale'}, {'BOTSID':'sales'})

    # Order number
    oout.put({'BOTSID':'sales','id': order_number})
    oout.put({'BOTSID':'sales','name': order_number})
    oout.put({'BOTSID':'sales','order': order_number})

    # Dates
    oout.put({'BOTSID':'sales','order_date': order_date}) # Order Date
    # Cancel after date # Not really used, ignoring
    # oout.put({'BOTSID':'sales','cancel_after_date':transform.datemask(inn.get({'BOTSID':'ST'},{'BOTSID':'DTM','DTM01':'001','DTM02':None}),'CCYYMMDD','CCYY-MM-DD')})
    # Requested ship date
    oout.put({'BOTSID':'sales','ship_date':transform.datemask(inn.get({'BOTSID':'ST'},{'BOTSID':'DTM','DTM01':'010','DTM02':None}),'CCYYMMDD','CCYY-MM-DD')})

    oout.put({'BOTSID':'sales','client_order_ref': program_ref}) # Program as reference
    oout.put({'BOTSID':'sales','currency': order_currency}) # Currency
    oout.put({'BOTSID':'sales','parnter_name': customer_name}) # Currency
    oout.put({'BOTSID':'sales','parnter_email': customer_email}) # Currency

    #loop over partys
    for partner in inn.getloop({'BOTSID':'ST'},{'BOTSID':'N1'}): 
        pou = oout.putloop({'BOTSID':'sales'},{'BOTSID':'partner'})
        type = partner.get({'BOTSID':'N1','N101':None})
        if type == 'FP':
            openerp_type = 'invoice'
        elif type == 'ST':
            openerp_type = 'delivery'
        elif type == 'BT':
            openerp_type = 'invoice'
        else:
            openerp_type = 'other'

        pou.put({'BOTSID':'partner','type':openerp_type})
        pou.put({'BOTSID':'partner','name1':partner.get({'BOTSID':'N1','N102':None})})
        pou.put({'BOTSID':'partner','name2':partner.get({'BOTSID':'N1'},{'BOTSID':'N2','N201':None})})
        pou.put({'BOTSID':'partner','address1':partner.get({'BOTSID':'N1'},{'BOTSID':'N3','N301':None})})
        pou.put({'BOTSID':'partner','address2':partner.get({'BOTSID':'N1'},{'BOTSID':'N3','N302':None})})
        pou.put({'BOTSID':'partner','city':partner.get({'BOTSID':'N1'},{'BOTSID':'N4','N401':None})})
        pou.put({'BOTSID':'partner','state':partner.get({'BOTSID':'N1'},{'BOTSID':'N4','N402':None})})
        pou.put({'BOTSID':'partner','zip':partner.get({'BOTSID':'N1'},{'BOTSID':'N4','N403':None})})
        pou.put({'BOTSID':'partner','country':partner.get({'BOTSID':'N1'},{'BOTSID':'N4','N404':None})})

    #loop over lines
    for po1 in inn.getloop({'BOTSID':'ST'},{'BOTSID':'PO1'}):
        lou = oout.putloop({'BOTSID':'sales'},{'BOTSID':'line'})
        lou.put({'BOTSID':'line','seq':po1.get({'BOTSID':'PO1','PO101':None})})
        lou.put({'BOTSID':'line','qty':po1.get({'BOTSID':'PO1','PO102':None})})
        lou.put({'BOTSID':'line','price':po1.get({'BOTSID':'PO1','PO104':None})})
        lou.put({'BOTSID':'line','product_sku':get_art_num(po1,'SK')}) # Product stock keeping unit (SKU)

    #loop over transaction totals
    for tot in inn.getloop({'BOTSID':'ST'},{'BOTSID':'CTT'}):
        tou = oout.putloop({'BOTSID':'sales'},{'BOTSID':'total'})
        tou.put({'BOTSID':'total','line_item_total':get_art_num(tot,'1')})
        tou.put({'BOTSID':'total','transaction_fee':get_art_num(tot,'TF')})
        tou.put({'BOTSID':'total','sales_tax':get_art_num(tot,'F7')})
        tou.put({'BOTSID':'total','handling_charges':get_art_num(tot,'OH')})
        tou.put({'BOTSID':'total','total_invoice_amount':get_art_num(tot,'5')})
