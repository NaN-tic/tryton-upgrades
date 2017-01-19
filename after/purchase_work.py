#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction
from trytond.pool import Pool
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

    Project = pool.get('project.work')
    PurchaseLine = pool.get('purchase.line')
    projects = Project.search([])
    to_save = []
    for project in projects:
        purchase_lines = []
        project.purchase_lines = []
        for line in project.sale_lines:
            purchase_lines += line.purchase_lines

        if purchase_lines:
            for pl in purchase_lines:
                project.purchase_lines += (pl, )
            to_save.append(project)
    Project.save(to_save)
