#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
import logging
from trytond import __version__

trytond_version = float('.'.join(__version__.split('.')[:2]))

Pool.start()
pool = Pool(dbname)
pool.init()

context = {'active_test': False}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

with Transaction().start(dbname, 1, context=context):
    Company = pool.get('company.company')
    ModelData = pool.get('ir.model.data')
    Category = pool.get('product.category')
    Template = pool.get('product.template')
    Account = pool.get('account.account')
    Tax = pool.get('account.tax')

    Payment = pool.get('account.payment')
    Line = pool.get('account.move.line')
    SepaMandate = pool.get('account.payment.sepa.mandate')

    BankNumber = pool.get('bank.account.number')

    cursor = Transaction().connection.cursor()

    # remove duplicated bank_number
    query = "select number_compact, count(1) from bank_account_number where type = 'iban' group by number_compact HAVING count(*) > 1"

    to_save = []
    to_delete = []
    to_delete_numbers = []

    cursor.execute(query)
    bank_rows = {}
    for number_compact, _ in cursor.fetchall():
        bank_numbers = BankNumber.search([
            ('number_compact', '=', number_compact)
            ], order=[('create_date', 'ASC')])

        bank_account = None
        for bank_number in bank_numbers:
            if bank_number.account.owners:
                bank_account = bank_number.account
                break

        if not bank_account:
            to_delete_numbers += bank_numbers

        for bank_number in bank_numbers:
            if not bank_number.account.owners:
                to_delete_numbers.append(bank_number)
                continue

            bank_account.owners += bank_number.account.owners
            bank_account.save()

            to_delete_numbers.append(bank_number)

    if to_delete_numbers:
        ids = [n.id for n in to_delete_numbers]
        query = "delete from bank_account_number where id in (%s)" % ','.join([str(id) for id in ids])
        cursor.execute(query)

    Transaction().commit()
