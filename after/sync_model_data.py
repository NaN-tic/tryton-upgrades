#!/usr/bin/env python
import os
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
import logging

Pool.start()
pool = Pool(dbname)
pool.init()

context = {}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

to_omit = []
if 'sync_model_data_omit' in os.environ:
    to_omit = str(os.environ['sync_model_data_omit']).split(',')


with Transaction().start(dbname, 0, context=context):
    Data = pool.get('ir.model.data')

    domain = []
    #domain += [('out_of_sync', '=', True)]
    if to_omit:
        domain += [('id', 'not in', to_omit)]
    datas = Data.search(domain)
    print('LEN: ', len(datas))
    Data.sync(datas)

    Transaction().commit()

    logger.info('Done')
