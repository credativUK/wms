import os
import sys
import shutil
import filecmp
import bots.botsglobal as botsglobal
import bots.botslib as botslib

def cleanoutputdir():
    ''' delete directory standard-out  'bots/botssys/out' (as indicated in bos.ini). ''' 
    botssys = botsglobal.ini.get('directories','botssys')
    shutil.rmtree(os.path.join(botssys,'outfile'),ignore_errors=True)    #remove whole output directory

def getreportlastrun():
    ''' Return the results of the last run as a dict.'''
    for row in botslib.query(u'''SELECT *
                            FROM    report
                            ORDER BY idta DESC
                            '''):
        return dict(row)
    raise Exception('no report')

def pretest(routestorun):
    cleanoutputdir()
    #cleanpreviousruns: for reports that are marked as 'acceptance'

def posttest(routestorun):
    #Compare run results

    #Compare outgoing files.
    #Run run first, save results in 'botssys/outfile' in 'botssys/infile' (so there is a directory 'botssys/infile/outfile'....)
    #than run again; files in bot directories will be compared.
    botssys = botsglobal.ini.get('directories','botssys')
    cmpobj = filecmp.dircmp(os.path.join(botssys,'outfile'), os.path.join(botssys,'infile/outfile'))
    cmpobj.report_full_closure()
