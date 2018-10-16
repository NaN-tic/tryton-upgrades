#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction
from trytond.pool import Pool
import trytond.tools as tools
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
    Company = pool.get('company.company')
    Configuration = pool.get('account.configuration')
    Account = pool.get('account.account')

    cursor = Transaction().connection.cursor()

    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            config = Configuration(1)
            cdigits = config.default_account_code_digits or 8

            for account in Account.search([('kind', '!=', 'view')]):
                if account.code and len(account.code) < cdigits:
                    digits = int(cdigits - len(account.code))
                    if '%' in account.code:
                        code = account.code.replace('%', '0' * (digits + 1))
                    else:
                        code = account.code + '0' * digits
                    query = "update account_account set code = '%s' where id = %s" % (code, account.id)
                    cursor.execute(query)

    Transaction().commit()

    logger.info('Done')
