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
    out.put({'BOTSID':'order'},{'BOTSID':'header','sender':inn.ta_info['frompartner']})
    out.put({'BOTSID':'order'},{'BOTSID':'header','receiver':inn.ta_info['topartner']})
    out.put({'BOTSID':'order'},{'BOTSID':'header','testindicator':inn.ta_info['testindicator']})

    #pick up document number. is used in bots to give 'document-view'
    docnum = inn.get({'BOTSID':'ST'},{'BOTSID':'BEG','BEG03':None})
    out.put({'BOTSID':'order'},{'BOTSID':'header','docnum':docnum})
    inn.ta_info['botskey']=docnum
    out.ta_info['botskey']=docnum

    docdtm = inn.get({'BOTSID':'ST'},{'BOTSID':'BEG','BEG05':None})
    docdtm = transform.datemask(docdtm,'CCYYMMDD','CCYY-MM-DD')
    out.put({'BOTSID':'order'},{'BOTSID':'header','docdtm':docdtm}) # Sale order date

    # Cancel after date
    out.put({'BOTSID':'order'},{'BOTSID':'header','cancel_after_date':transform.datemask(inn.get({'BOTSID':'ST'},{'BOTSID':'DTM','DTM01':'001','DTM02':None}),'CCYYMMDD','CCYY-MM-DD')})

    # Requested ship date
    out.put({'BOTSID':'order'},{'BOTSID':'header','requested_ship_date':transform.datemask(inn.get({'BOTSID':'ST'},{'BOTSID':'DTM','DTM01':'010','DTM02':None}),'CCYYMMDD','CCYY-MM-DD')})

    out.put({'BOTSID':'order'},{'BOTSID':'header','program':inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'PID','REF02':None})}) # Program as reference

    out.put({'BOTSID':'order'},{'BOTSID':'header','customer_email':inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'EM','REF02':None})}) # Customer email
    out.put({'BOTSID':'order'},{'BOTSID':'header','customer_name':inn.get({'BOTSID':'ST'},{'BOTSID':'REF','REF01':'NM','REF02':None})}) # Customer name

    #loop over partys
    for party in inn.getloop({'BOTSID':'ST'},{'BOTSID':'N1'}): 
        pou = out.putloop({'BOTSID':'order'},{'BOTSID':'header'},{'BOTSID':'partys'},{'BOTSID':'party'})
        pou.put({'BOTSID':'party','name1':party.get({'BOTSID':'N1','N102':None})})
        pou.put({'BOTSID':'party','name2':party.get({'BOTSID':'N1'},{'BOTSID':'N2','N201':None})})
        pou.put({'BOTSID':'party','address1':party.get({'BOTSID':'N1'},{'BOTSID':'N3','N301':None})})
        pou.put({'BOTSID':'party','address2':party.get({'BOTSID':'N1'},{'BOTSID':'N3','N302':None})})
        pou.put({'BOTSID':'party','city':party.get({'BOTSID':'N1'},{'BOTSID':'N4','N401':None})})
        pou.put({'BOTSID':'party','state':party.get({'BOTSID':'N1'},{'BOTSID':'N4','N402':None})})
        pou.put({'BOTSID':'party','pcode':party.get({'BOTSID':'N1'},{'BOTSID':'N4','N403':None})})
        pou.put({'BOTSID':'party','country':party.get({'BOTSID':'N1'},{'BOTSID':'N4','N404':None})})

    #loop over lines
    for po1 in inn.getloop({'BOTSID':'ST'},{'BOTSID':'PO1'}):
        lou = out.putloop({'BOTSID':'order'},{'BOTSID':'header'},{'BOTSID':'lines'},{'BOTSID':'line'})
        lou.put({'BOTSID':'line','linenum':po1.get({'BOTSID':'PO1','PO101':None})})
        lou.put({'BOTSID':'line','ordqua':po1.get({'BOTSID':'PO1','PO102':None})})
        lou.put({'BOTSID':'line','price':po1.get({'BOTSID':'PO1','PO104':None})})
        lou.put({'BOTSID':'line','product_sku':get_art_num(po1,'SK')}) # Product stock keeping unit (SKU)

    #loop over transaction totals
    for tot in inn.getloop({'BOTSID':'ST'},{'BOTSID':'CTT'}):
        tou = out.putloop({'BOTSID':'order'},{'BOTSID':'header'},{'BOTSID':'totals'},{'BOTSID':'total'})
        tou.put({'BOTSID':'total','line_item_total':get_art_num(tot,'1')})
        tou.put({'BOTSID':'total','transaction_fee':get_art_num(tot,'TF')})
        tou.put({'BOTSID':'total','sales_tax':get_art_num(tot,'F7')})
        tou.put({'BOTSID':'total','handling_charges':get_art_num(tot,'OH')})
        tou.put({'BOTSID':'total','total_invoice_amount':get_art_num(tot,'5')})

