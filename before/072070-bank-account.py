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

    # 1. move data to new
    query = 'alter table  "party_party-bank_account-company" ADD COLUMN IF NOT EXISTS payable_bank_account int';
    query = 'alter table  "party_party-bank_account-company" ADD COLUMN IF NOT EXISTS receivable_bank_account int';
    cursor.execute(query)

    query = 'select account, owner, company, payable_bank_account, receivable_bank_account from "bank_account-party_party"'
    cursor.execute(query)
    bank_rows = {}
    for account_id, owner_id, company_id, is_payable_bank_account, is_receivable_bank_account  in cursor.fetchall():
        query2 = 'select id from "party_party-bank_account-company" where party = %s and company = %s' % (owner_id, company_id)
        cursor.execute(query2)

        has_id = None
        for row in cursor.fetchall():
            has_id = row[0]

        if has_id:
            if is_payable_bank_account:
                query = 'update "party_party-bank_account-company" set payable_bank_account = %s where id = %s' % (account_id, has_id);
                cursor.execute(query)
            if is_receivable_bank_account:
                query = 'update "party_party-bank_account-company" set receivable_bank_account = %s where id = %s' % (account_id, has_id);
                cursor.execute(query)
        else:
            query = 'insert into "party_party-bank_account-company" (party, company, payable_bank_account, receivable_bank_account) values (%s, %s, %s, %s)' % (owner_id, company_id, account_id if is_payable_bank_account else 'null', account_id if is_receivable_bank_account else 'null')
            cursor.execute(query)

    Transaction().commit()
