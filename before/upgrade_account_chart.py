#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond import __version__
from trytond.transaction import Transaction
from trytond.pool import Pool
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
    ModelData = pool.get('ir.model.data')
    Configuration = pool.get('account.configuration')
    Account = pool.get('account.account')
    AccountTemplate = pool.get('account.account.template')

    UpdateChart = pool.get('account.update_chart', type='wizard')

    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            template = AccountTemplate(ModelData.get_id('account_es', 'pgc_0'))
            account, = Account.search([('template', '=', template)], limit=1)
            config = Configuration(1)

            session_id, _, _ = UpdateChart.create()
            update_chart = UpdateChart(session_id)
            update_chart.start.account = account
            update_chart.start.account_code_digits = config.default_account_code_digits
            logger.info('%s: Upgrading Account Chart' % (company.rec_name))
            update_chart.transition_update()
            logger.info('%s: End Account Chart' % (company.rec_name))

    if trytond_version > 3.8:
        Transaction().commit()
    else:
        Transaction().cursor.commit()

    logger.info('Done')
