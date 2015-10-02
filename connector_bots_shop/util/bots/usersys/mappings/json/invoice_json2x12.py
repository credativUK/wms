#mapping-script
import bots.transform as transform
import re

def main(inn,out):
    #sender, receiver is correct via QUERIES in grammar. 
    out.put({'BOTSID':'ST','ST01':'810','ST02':out.ta_info['reference'].zfill(4)})

    INV_REF = re.sub(r'[^a-zA-Z0-9 ]', r'', inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices','ref':None}) or "")
    SALE_REF = inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices','sale':None}) or ""
    DATE_INV = transform.datemask(inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices','date':None}),'CCYY-MM-DD','CCYYMMDD')
    DATE_SALE = transform.datemask(inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices','sale_date':None}),'CCYY-MM-DD HH:mm','CCYYMMDD')

    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG01': DATE_INV})
    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG02': INV_REF})
    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG03': DATE_SALE})
    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG04': SALE_REF})
    
    # DTM01:011 is "ship date"
    out.put({'BOTSID':'ST'},{'BOTSID':'DTM','DTM01':'011','DTM02': DATE_SALE})

    # Partner
    pou = out.putloop({'BOTSID':'ST'},{'BOTSID':'N1'})
    pou.put({'BOTSID':'N1','N101': 'ST'})
    pou.put({'BOTSID':'N1','N102':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','name':None})})
    #pou.put({'BOTSID':'N1'},{'BOTSID':'N2','N201':''}) # No name2
    pou.put({'BOTSID':'N1'},{'BOTSID':'N3','N301':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','street1':None})})
    pou.put({'BOTSID':'N1'},{'BOTSID':'N3','N302':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','street2':None})})
    pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N401':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','city':None})})
    pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N402':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','state':None})})
    pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N403':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','zip':None})})
    pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N404':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'partner','country':None})})

    #loop over lines***************************************
    for lin in inn.getloop({'BOTSID':'invoice'},{'BOTSID':'invoices'},{'BOTSID':'lines'}):
        lou = out.putloop({'BOTSID':'ST'},{'BOTSID':'IT1'}) 
        lou.put({'BOTSID':'IT1','IT101':lin.get({'BOTSID':'lines','seq':None})})
        lou.put({'BOTSID':'IT1','IT103':'EA','IT102':lin.get({'BOTSID':'lines','product_qty':None})})
        lou.put({'BOTSID':'IT1','IT104':lin.get({'BOTSID':'lines','total':None})})
        lou.put({'BOTSID':'IT1','IT106':'SK','IT107':lin.get({'BOTSID':'lines','product_sku':None})})
        lou.put({'BOTSID':'IT1','IT108':'SK','IT109':lin.get({'BOTSID':'lines','product_sku':None})})
        lou.put({'BOTSID':'IT1','IT110':'SK','IT111':lin.get({'BOTSID':'lines','product_sku':None})})

    out.put({'BOTSID':'ST'},{'BOTSID':'TDS','TDS01':inn.get({'BOTSID':'invoice'},{'BOTSID':'invoices','total':None})})

    out.put({'BOTSID':'ST'},{'BOTSID':'ISS','ISS02':'EA','ISS01':out.getcountsum({'BOTSID':'ST'},{'BOTSID':'IT1','IT102':None}) })  #bots counts total Number of Units Shipped 
    out.put({'BOTSID':'ST'},{'BOTSID':'CTT','CTT01':out.getcountoccurrences({'BOTSID':'ST'},{'BOTSID':'IT1'}) }) #bots counts number of line items/IT1 segments 
    out.put({'BOTSID':'ST'},{'BOTSID':'SE','SE01':out.getcount()+1,'SE02':out.ta_info['reference'].zfill(4)})  #SE01: bots counts the segments produced in the X12 message.
