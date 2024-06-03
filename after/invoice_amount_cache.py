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

with Transaction().start(dbname, 0, context=context) as transaction:
    Invoice = pool.get('account.invoice')
    invoices = Invoice.search([('state', 'in', ['posted', 'paid'])])
    for invoice in invoices:
        # invoice.untaxed_amount_cache = invoice.untaxed_amount
        # invoice.tax_amount_cache = invoice.tax_amount
        # invoice.total_amount_cache = invoice.total_amount

        cursor = transaction.connection.cursor()

        # update with sql because old databases could raise DomainError (oldest invoices)
        query = 'update account_invoice set untaxed_amount_cache=%s, tax_amount_cache=%s, total_amount_cache=%s where id = %s' % (invoice.untaxed_amount, invoice.tax_amount, invoice.total_amount, invoice.id)
        cursor.execute(query)
    # Invoice.save(invoices)
    transaction.commit()
