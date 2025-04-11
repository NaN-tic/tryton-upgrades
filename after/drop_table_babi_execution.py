#!/usr/bin/env python
import sys
import datetime
#from itertools import izip

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
    cursor = Transaction().connection.cursor()

    query = """
        SELECT 'DROP TABLE IF EXISTS ' || quote_ident(tablename) || ' CASCADE;'
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'babi_execution_%';
        """
    cursor.execute(query)
    for row in cursor.fetchall():
        cursor.execute(row[0])
    Transaction().commit()
