#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
digits = sys.argv[3] if len(sys.argv) == 4 else 6
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
    ModelData = pool.get('ir.model.data')
    Configuration = pool.get('account.configuration')
    Account = pool.get('account.account')
    AccountTemplate = pool.get('account.account.template')
    Party = pool.get('party.party')

    party = Party.search([('name', '=', 'Generic for Party required Accounts')])
    if not party:
        party = Party(name='Generic for Party required Accounts')
        party.save()
    else:
        party, = party

    cursor = Transaction().connection.cursor()
    cursor.execute(''' update account_move_line set party=%s where id in (
        select l.id from account_move_line l, account_account a where
        l.account=a.id and a.party_required and l.party is null) ''' %
        party.id)

    UpdateChart = pool.get('account.update_chart', type='wizard')

    Account.parent.left = None
    Account.parent.right = None

    domain = []
    child_companies = Company.search([('parent', '!=', None)])
    if child_companies:
        domain.append(('parent', '!=', None))

    for company in Company.search(domain):
        logger.info("company %s" % company.id)
        with Transaction().set_context(company=company.id):

            template = AccountTemplate(ModelData.get_id('account_es', 'pgc_0'))
            account, = Account.search([('template', '=', template)], limit=1)
            config = Configuration(1)

            if not config.default_account_code_digits:
                config.default_account_code_digits = digits
                config.force_digits = True
                config.save()

            session_id, _, _ = UpdateChart.create()
            update_chart = UpdateChart(session_id)
            update_chart.start.account = account
            update_chart.start.account_code_digits = config.default_account_code_digits
            #print(update_chart.start.account_code_digits)
            logger.info('%s: Upgrading Account Chart' % (company.rec_name))
            update_chart.transition_update()
            logger.info('%s: End Account Chart' % (company.rec_name))

            Transaction().commit()

    Account.parent.left = 'left'
    Account.parent.right = 'right'

    for company in Company.search(domain):
        logger.info("company %s" % company.id)
        logger.info('%s: Rebuild tree' % (company.rec_name))
        with Transaction().set_context(company=company.id):
            Account._rebuild_tree('parent', None, 0)
        logger.info('%s: End rebuild tree' % (company.rec_name))

    logger.info('Done')
