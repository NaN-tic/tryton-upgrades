#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model.modelstorage import DomainValidationError
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

    query = "SELECT id, resource FROM ir_attachment"
    cursor.execute(query)
    for id, resource in cursor.fetchall():
        model, _id = resource.split(',')
    
        try:
            Model = pool.get(model)
        except Exception as e:
            continue
        
        exist = Model.search([('id', '=', _id)], count=True)
        if exist:
            continue
        query = "delete FROM ir_attachment where id = %s" % id
        cursor.execute(query)
    transaction.commit()
