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

context={'active_test': False}
with Transaction().start(dbname, 0, context=context):

    Company = Pool().get('company.company')
    User = Pool().get('res.user')

    for company in Company.search([]):
        logger.info("company %s" % company.id)
        with Transaction().set_context(company=company.id):
                admin, = User.search([('login', '=', 'admin'),], limit=1)
                u, = User.copy([admin])
                u.name = company.party.name + " (Usuari d'empresa)"
                u.login = company.party.name
                u.company = company
                u.main_company = company
                u.save()
                company.company_user = u
                company.save()

    Transaction().commit()
