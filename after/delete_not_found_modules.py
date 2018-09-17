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

with Transaction().start(dbname, 0, context=context):
    Company = pool.get('company.company')
    Module = pool.get('ir.module')
    ModuleDependency = pool.get('ir.module.dependency')

    cursor = Transaction().connection.cursor()

    to_delete = []
    for module in Module.search([('state', '=', 'not activated')]):
        try:
            with tools.file_open(os.path.join(module.name, 'tryton.cfg')) as fp:
                pass
        except:
            to_delete.append(module)

    logger.info('Modules to delete: %s' % ','.join([m.name for m in to_delete]))

    if to_delete:
        dependencies = ModuleDependency.search([('module', 'in', to_delete)])
        ModuleDependency.delete(dependencies)
        Module.delete(to_delete)

    Transaction().commit()

    logger.info('Done')
