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
from trytond.tools import grouped_slice

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

with Transaction().start(dbname, 0, context=context):
    Invoice = pool.get('account.invoice')
    Company = pool.get('company.company')

    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            invoices = Invoice.search([
                ('invoice_report_format', '=', None),
                ('state', 'in', ['paid', 'posted']),
                ('type', '=', 'out'),
                ('company', '=', company),
                ])

            for sub_invoices in grouped_slice(invoices):
                for invoice in sub_invoices:
                    invoice.print_invoice()

    Transaction().commit()

    logger.info('Done')
