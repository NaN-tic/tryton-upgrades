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
    Invoice = pool.get('account.invoice')
    PaymentType = pool.get('account.payment.type')
    try:
        Contract = pool.get('contract')
    except KeyError:
        Contract = None

    BankNumber = pool.get('bank.account.number')

    cursor = Transaction().connection.cursor()

    # 1. drop _sql_constraints
    # 2. rename account2 to account in case before upgrade rename columns
    # 3. rename number_compact2 to number_compact in case before upgrade rename columns
    # 4. remove duplicated iban codes
    query = "ALTER TABLE bank_account_number DROP CONSTRAINT IF EXISTS bank_account_number_number_iban_exclude"
    cursor.execute(query)
    query = "ALTER TABLE bank_account_number DROP CONSTRAINT IF EXISTS bank_account_number_account_iban_exclude"
    cursor.execute(query)

    query = "SELECT 1 FROM information_schema.columns  WHERE table_name='bank_account_number' and column_name='number_compact2'"
    cursor.execute(query)
    if cursor.fetchone():
        query = "alter table bank_account_number drop column number_compact"
        cursor.execute(query)
        query = "alter table bank_account_number rename number_compact2 to number_compact"
        cursor.execute(query)

    query = "SELECT 1 FROM information_schema.columns  WHERE table_name='bank_account_number' and column_name='account2'"
    cursor.execute(query)
    if cursor.fetchone():
        query = "alter table bank_account_number drop column account"
        cursor.execute(query)
        query = "alter table bank_account_number rename account2 to account"
        cursor.execute(query)

    query = "select number_compact, count(*) from bank_account_number where type = 'iban' group by number_compact HAVING count(*) > 1"

    cursor.execute(query)
    for number_compact, _ in cursor.fetchall():
        bank_numbers = BankNumber.search([
            ('number_compact', '=', number_compact)
            ], order=[('create_date', 'ASC')])
        bank_number = bank_numbers[0]
        bank_account = bank_number.account
        bank_number_to_delete = bank_numbers[1:]

        bank_number_mandates = SepaMandate.search([
            ('account_number', '=', bank_number),
            ])

        for bn in bank_number_to_delete:
            ba = bn.account

            query = 'update "bank_account-party_party" set account = %s where account = %s' % (bank_account.id, ba.id)
            cursor.execute(query)

            query = 'update "party_party-bank_account-company" set receivable_company_bank_account = %s where receivable_company_bank_account = %s' % (bank_account.id, ba.id)
            cursor.execute(query)
            query = 'update "party_party-bank_account-company" set payable_company_bank_account = %s where payable_company_bank_account = %s' % (bank_account.id, ba.id)
            cursor.execute(query)

            invoices = Invoice.search([('bank_account', '=', ba)])
            if invoices:
                query = 'update account_invoice set bank_account = %s where id in (%s)' % (bank_account.id, ', '.join(str(i.id) for i in invoices))
                cursor.execute(query)

            payment_types = PaymentType.search([('bank_account', '=', ba)])
            if payment_types:
                query = 'update account_payment_type set bank_account = %s where id in (%s)' % (bank_account.id, ', '.join(str(p.id) for p in payment_types))
                cursor.execute(query)

            lines = Line.search([('bank_account', '=', ba)])
            if lines:
                query = 'update account_move_line set bank_account = %s where id in (%s)' % (bank_account.id, ', '.join(str(l.id) for l in lines))
                cursor.execute(query)

            payments = Payment.search([('bank_account', '=', ba)])
            if payments:
                mand = bank_number_mandates[0].id if bank_number_mandates else 'null'
                query = 'update account_payment set bank_account = %s, sepa_mandate = %s where id in (%s)' % (bank_account.id, mand, ', '.join(str(p.id) for p in payments))
                cursor.execute(query)

            if Contract:
                contracts = Contract.search([('bank_account', '=', ba)])
                if contracts:
                    query = 'update contract set bank_account = %s where id in (%s)' % (bank_account.id, ', '.join(str(c.id) for c in contracts))
                    cursor.execute(query)

            mandates = SepaMandate.search([
                ('account_number', '=', bn),
                ])
            if mandates:
                query = 'delete from account_payment_sepa_mandate where id in (%s)' % (', '.join(str(m.id) for m in mandates))
                cursor.execute(query)

        query = "delete from bank_account_number where id in (%s)" % (', '.join(str(b.id) for b in bank_number_to_delete))
        cursor.execute(query)

        query = "delete from bank_account where id in (%s)" % (', '.join(str(b.account.id) for b in bank_number_to_delete if b.account))
        cursor.execute(query)

    query = "select account, count(*) from bank_account_number where type = 'iban' group by account HAVING count(*) > 1"

    cursor.execute(query)
    for account, _ in cursor.fetchall():
        bank_numbers = BankNumber.search([
            ('account', '=', account)
            ], order=[('create_date', 'ASC')])
        bank_number = bank_numbers[0]
        bank_number_to_inactive = bank_numbers[1:]

        query = "update bank_account_number set type = 'other' where id in (%s)" % (', '.join(str(b.id) for b in bank_number_to_inactive))
        cursor.execute(query)

    query = 'select account, owner, company from "bank_account-party_party" group by account, owner, company having count(1) > 1'
    cursor.execute(query)
    for account, owner, company in cursor.fetchall():
        query = 'select id from "bank_account-party_party" where account = %s and owner = %s and company = %s order by id ASC;' % (account, owner, company)
        cursor.execute(query)
        accounts = cursor.fetchall()
        accounts.pop(0)
        if len(accounts) >= 1:
            for id_ in accounts:
                query = 'delete from "bank_account-party_party" where id = %s' % id_
                cursor.execute(query)

    if trytond_version > 3.8:
        Transaction().commit()
    else:
        Transaction().cursor.commit()
