#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model.modelstorage import DomainValidationError
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

with Transaction().start(dbname, 0, context=context) as transaction:
    Template = pool.get('product.template')
    Company = pool.get('company.company')
    cursor = transaction.connection.cursor()

    companys = Company.search([])

    query = 'SELECT id FROM product_template WHERE _temp_supply_on_sale = True;'
    cursor.execute(query)
    templates = cursor.fetchall()

    to_save = []
    for company in companys:
        for template in templates:
            query = "insert into product_template_supply_on_sale (template, company, supply_on_sale) values (%s, %s, 'always')" % (template[0], company.id)
            cursor.execute(query)
    transaction.commit()
