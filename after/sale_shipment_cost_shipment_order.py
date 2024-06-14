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

with Transaction().start(dbname, 0, context=context) as transaction:

    cursor = transaction.connection.cursor()

    Company = pool.get('company.company')
    Sale = pool.get('sale.sale')
    # to_order = []
    for company in Company.search([]):
        sales = Sale.search([('state', 'not in', ['done', 'cancelled']), ('shipment_cost_method', '=', 'order'), ('company', '=', company.id) ])
        for sale in sales:
            for shipment in sale.shipments:
                if shipment.cost_method == 'shipment':
                    # to_order.append(shipment.id)
                    query = "update stock_shipment_out set cost_method = 'order' where id = %s" % shipment.id
                    cursor.execute(query)

    transaction.commit()
