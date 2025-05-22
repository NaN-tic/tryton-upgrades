#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.tools import grouped_slice, reduce_ids
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
    Company = pool.get('company.company')
    cursor = transaction.connection.cursor()

    company_ids = [c.id for c in Company.search([])]
    for company_id in company_ids:
        with Transaction().set_context(company=company_id):

            query = "SELECT id FROM account_invoice WHERE company = %s and state in ('posted', 'paid') and untaxed_amount_cache is null" % (company_id)
            cursor.execute(query)
            ids = [row[0] for row in cursor.fetchall()]
            print('company, ', company_id, ' Total, ', len(ids))

            i = 0
            for sub_ids in grouped_slice(ids):
                i += 1
                print('Bloc, ', i)
                invoices = Invoice.browse(sub_ids)
                for invoice in invoices:
                    # invoice.untaxed_amount_cache = invoice.untaxed_amount
                    # invoice.tax_amount_cache = invoice.tax_amount
                    # invoice.total_amount_cache = invoice.total_amount

                    # update with sql because old databases could raise DomainError (oldest invoices)
                    query = 'update account_invoice set untaxed_amount_cache=%s, tax_amount_cache=%s, total_amount_cache=%s where id = %s' % (invoice.untaxed_amount, invoice.tax_amount, invoice.total_amount, invoice.id)
                    cursor.execute(query)
                transaction.commit()
