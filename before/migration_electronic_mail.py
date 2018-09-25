#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction
from trytond.pool import Pool
import trytond.tools as tools
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

with Transaction().start(dbname, 1, context=context):
    cursor = Transaction().cursor
    db_name = Transaction().cursor.dbname

    mail_dir = os.path.join(CONFIG.get('database', 'path'), db_name, 'email')
    if os.path.isdir(mail_dir):
        os.remove(mail_dir)

    query = "ALTER TABLE if exists electronic_mail_template DROP COLUMN draft_mailbox;"
    cursor.execute(query)
    query = "ALTER TABLE if exists electronic_mail_template DROP COLUMN mailbox;"
    cursor.execute(query)
    query = "ALTER TABLE if exists electronic_mail_template DROP COLUMN mailbox_outbox;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail_mailbox_read_res_user;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail_mailbox_write_res_user;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail_configuration_company;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail_configuration;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail_mailbox_mailbox;"
    cursor.execute(query)
    query = "DROP TABLE if exists electronic_mail_mailbox;"
    cursor.execute(query)

    Transaction().cursor.commit()

    logger.info('Done')
