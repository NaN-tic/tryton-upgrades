#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction
from trytond.pool import Pool
import logging

Pool.start()
pool = Pool(dbname)
pool.init()

context = {}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s'
    '- %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

with Transaction().start(dbname, 0, context=context) as transaction:
    ProductPriceList = pool.get('product.price_list')
    ProductPriceListLine = pool.get('product.price_list.line')

    for price_list in ProductPriceList.search([]):
        create_line = False
        if price_list.lines:
            line = price_list.lines[-1:][0]
            if line.formula != 'unit_price':
                create_line = True
        else:
            create_line = True
        if create_line:
            line = ProductPriceListLine()
            line.price_list = price_list
            line.formula = 'unit_price'
            line.sequence = 9999999
            line.save()

    transaction.commit()
