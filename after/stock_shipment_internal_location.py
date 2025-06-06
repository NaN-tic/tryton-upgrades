#!/usr/bin/env python
import sys

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

context={'active_test': False}
with Transaction().start(dbname, 0, context=context) as transaction:
    pool = Pool()
    Shipment = pool.get('stock.shipment.internal')

    shipments = Shipment.search([('state', 'not in', ['request', 'draft'])])
    for shipment in shipments:
        state = shipment.state
        shipment.state = 'draft'
        shipment.internal_transit_location = shipment.transit_location
        shipment.state = state
    Shipment.save(shipments)

    Transaction().commit()
