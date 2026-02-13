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
    ModelData = pool.get('ir.model.data')
    Location = pool.get('stock.location')

    cursor = Transaction().connection.cursor()

    model_data, = ModelData.search([
        ('fs_id', '=', 'location_transit'),
        ('module', '=', 'stock'),
        ])
    transit_loc = Location(model_data.db_id)

    cursor = Transaction().connection.cursor()

    shipments = Shipment.search([('state', 'not in', ['request', 'draft'])])
    for shipment in shipments:
        shipment.state = 'draft'
        transit_location = shipment.on_change_with_transit_location()
        if not transit_location:
            continue
        query = 'update stock_shipment_internal set internal_transit_location = %s where id = %s' % (transit_location.id, shipment.id)
        cursor.execute(query)

    Transaction().commit()
