#!/usr/bin/env python
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


with Transaction().start(dbname, 1, context=context):
    ProductIdentifier = pool.get('product.identifier')
    Product = pool.get('product.product')

    cursor = Transaction().connection.cursor()

    codes = ProductIdentifier.search([])
    values = dict(((x.type, x.code), x) for x in codes)

    code_types = [x[0] for x in ProductIdentifier.type.selection]

    to_create = []
    cursor.execute("select barcode, number, product, active from product_code")
    for x in cursor.fetchall():
        barcode, number, product, active = x
        barcode = 'ean' if barcode == 'EAN13' else barcode.lower()
        if barcode not in code_types:
            barcode = None

        key = (barcode, number)
        if key in values:
            continue

        pidentifier = ProductIdentifier()
        pidentifier.type = barcode
        pidentifier.product = Product(product)
        pidentifier.code = number
        to_create.append(pidentifier._save_values)

    if to_create:
        ProductIdentifier.create(to_create)

    Transaction().commit()
