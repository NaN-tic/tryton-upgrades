#!/usr/bin/env python
import sys

# Migration from 6.2 to 6.4
# https://discuss.tryton.org/t/migration-from-6-2-to-6-4/5241/5

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
    Payment = pool.get('account.payment')
    Module = pool.get('ir.module')

    # trytond.exceptions.UserError: Payment "1648" can not be modified because its mandate "RUM0000006" is canceled. -
    # trytond.model.modelstorage.DomainValidationError: The value for field "Bank Account" in "Payment" is not valid according to its domain. -

    # required account_payment_clearing activated
    if hasattr(Payment, 'update_reconciled'):
        payment_sepa_es = Module.search([
            ('name', '=', 'account_payment_sepa_es'),
            ('state', '=', 'activated'),
            ], limit=1)

        if payment_sepa_es:
            domain = ['OR',
                ('sepa_mandate', '=', None),
                ('sepa_mandate.state', '!=', 'cancelled'),
                ]
        else:
            domain = []

        payments = Payment.search(domain)

        for payment in payments:
            try:
                Payment.update_reconciled([payment])
            except DomainValidationError:
                pass
        transaction.commit()
