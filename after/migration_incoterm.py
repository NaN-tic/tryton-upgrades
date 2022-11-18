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
    Company = pool.get('company.company')
    User = pool.get('res.user')
    Party = pool.get('party.party')
    Address = pool.get('party.address')

    cursor = transaction.connection.cursor()

    query = "select incoterm_place from sale_sale where incoterm_place is not null group by incoterm_place";
    cursor.execute(query)

    party = Party()
    party.name = 'Incoterm Dummy'
    party.active = False
    party.save()

    addresses = {}
    for row in cursor.fetchall():
        address = Address()
        address.party = party
        address.city = row[0]
        address.save()
        addresses[row[0]] = address

    query = "select id, incoterm_place from sale_sale where incoterm_place is not null";
    cursor.execute(query)

    for row in cursor.fetchall():
        incoterm_location = addresses[row[1]]
        query = 'update sale_sale set incoterm_location = %s where id = %s' % (incoterm_location.id, row[0]);
        cursor.execute(query)

    Transaction().commit()
