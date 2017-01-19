#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction
from trytond.pool import Pool
import logging
from trytond.pyson import PYSONEncoder

Pool.start()
pool = Pool(dbname)
pool.init()

context = {'company': 1}

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

    pool = Pool()
    Rule = pool.get('ir.rule.group')

    groups = Rule.search([('create_uid', '>', 0)])
    for group in groups:
        for rule in group.rules:
            rule.domain = PYSONEncoder().encode(eval(rule.domain))
            rule.save()
