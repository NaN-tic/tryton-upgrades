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

with Transaction().start(dbname, 0, context=context) as transaction:
    Move = pool.get('stock.move')

    ids = []
    moves = Move.search([
        # ('currency', '=', None), # TODO uncomment in case moves has currency not required
        ('state', 'not in', ['done', 'cancelled']), # TODO remove domain in case user do copy oldest shipments
        ])
    for move in moves:
        if not move.unit_price_required:
            ids.append(str(move.id))
    if ids:
        query = 'update stock_move set unit_price = null, currency = null where id in (%s)' % ','.join(ids)

        cursor = transaction.connection.cursor()
        cursor.execute(query)
        transaction.commit()
