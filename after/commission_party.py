#!/usr/bin/env python
import sys

"""
Copy party_commission_agent to party_party_commission_agent tables
because not is a MultiValue field
"""

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
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

with Transaction().start(dbname, 0, context=context):
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id

with Transaction().start(dbname, 0, context=context) as transaction:

    # CommissionAgent = pool.get('party.party.commission.agent')
    # Party = pool.get('party.party')
    cursor = transaction.connection.cursor()

    # reset values
    query = 'delete from party_party_commission_agent';
    cursor.execute(query)

    query = 'select party, agent from party_commission_agent';
    cursor.execute(query)
    for row in cursor.fetchall():
        # set company = 1
        query = 'insert into party_party_commission_agent (party, agent, company) values (%s, %s, 1)' % (row[0], row[1]);
        cursor.execute(query)

    transaction.commit()
