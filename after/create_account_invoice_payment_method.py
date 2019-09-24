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
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

context={'active_test': True}
with Transaction().start(dbname, 1, context=context):
    Data = Pool().get('ir.model.data')
    ModelField = Pool().get('ir.model.field')
    Account = Pool().get('account.account')
    Company = Pool().get('company.company')
    Journal = Pool().get('account.journal')
    PaymentMethod = Pool().get('account.invoice.payment.method')
    User = pool.get('res.user')

    cursor = Transaction().connection.cursor()

    user, = User.search([('login', '=', 'admin')], limit=1)

    # credit_account_field, = ModelField.search([
    #     ('name', '=', 'credit_account'),
    #     ('model.model', '=', 'account.account'),
    #     ], limit=1)
    # debit_account_field, = ModelField.search([
    #     ('name', '=', 'debit_account'),
    #     ('model.model', '=', 'account.account'),
    #     ], limit=1)
    pgc_570_child, = Data.search([
        ('fs_id', '=', 'pgc_570_child'),
        ('module', '=', 'account_es'),
        ], limit=1)

    query = "select imf.id from ir_model_field as imf left join ir_model as im on im.id = imf.model where imf.name = 'credit_account' and im.model = 'account.journal'"
    cursor.execute(query)
    results = cursor.fetchone()
    credit_account_field_id = results[0] if results else pgc_570_child.id

    query = "select imf.id from ir_model_field as imf left join ir_model as im on im.id = imf.model where imf.name = 'debit_account' and im.model = 'account.journal'"
    cursor.execute(query)
    results = cursor.fetchone()
    debit_account_field_id = results[0] if results else pgc_570_child.id

    for company in Company.search([]):
        logger.info("company %s" % company.id)
        user.main_company=company.id
        user.company = company.id
        user.save()
        with Transaction().set_context(company=company.id):
            account_570 = Account.search([
                ('template', '=', pgc_570_child.db_id),
                ('company', '=', company.id),
                ], limit=1)

            if account_570:
                account_570, = account_570

            to_create = []
            for journal in Journal.search([('type', '=', 'cash')]):

                query = "select value from ir_property where res = 'account.journal,%s' and field = %s and company=%s" % (journal.id, credit_account_field_id, company.id);
                cursor.execute(query)
                credit_results = cursor.fetchone()
                credit_account = int(credit_results[0][16:]) if results else account_570 and account_570.id
                query = "select value from ir_property where res = 'account.journal,%s' and field = %s and company=%s" % (journal.id, debit_account_field_id, company.id);
                cursor.execute(query)
                debit_results = cursor.fetchone()
                debit_account = int(debit_results[0][16:]) if results else account_570 and account_570.id

                if not (credit_account and debit_account):
                    continue
                payment_method = PaymentMethod()
                payment_method.name = journal.code + "-" + (company.party.name)
                payment_method.company = company
                payment_method.journal = journal
                payment_method.credit_account = credit_account
                payment_method.debit_account = debit_account

                to_create.append(payment_method._save_values)

            if to_create:
                PaymentMethod.create(to_create)

    Transaction().commit()
