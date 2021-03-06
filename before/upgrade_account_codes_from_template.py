#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond import __version__
from trytond.pool import Pool
from trytond.transaction import Transaction
import trytond.tools as tools
import logging

trytond_version = float('.'.join(__version__.split('.')[:2]))

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
    Template = pool.get('account.account.template')

    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            config = Configuration(1)

            to_write = []
            with Transaction().set_context(active_test=False):
                for template in Template.search([('code', '!=', None)]):
                    digits = config.default_account_code_digits
                    digits = int(digits - len(template.code))
                    code = template.code

                    if template.kind != 'view':
                        if '%' in template.code:
                            new_code = code.replace('%', '0' * (digits + 1))
                        else:
                            new_code = code + '0' * digits
                    else:
                        new_code = code

                    accounts = Account.search([
                        ('code', '=', new_code),
                        ('template', '=', None),
                        # ('kind', '=', template.kind),
                        ], limit=1)

                    if accounts:
                        account, = accounts
                        to_write.extend(([account], {
                            'template': template,
                            }))
                        logger.info('%s: %s : ID %s' % (company.rec_name, new_code, account.id))

                for account in Account.search([('template', '=', None)]):
                    templates = Template.search([('code', '=', account.code)], limit=1)
                    if templates:
                        template, = templates
                        to_write.extend(([account], {
                            'template': template,
                            }))
                        logger.info('%s: Tpl ID %s : ID %s' % (company.rec_name, template.id, account.id))

            logger.info('%s: Upgrading Account from Template' % (company.rec_name))

            if to_write:
                Account.write(*to_write)

    if trytond_version > 3.8:
        Transaction().commit()
    else:
        Transaction().cursor.commit()

    logger.info('Done')
