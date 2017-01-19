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
    ShipmentWork = pool.get('shipment.work')
    Project = pool.get('project.work')
    Contract = pool.get('contract')
    ContractLine = pool.get('contract.line')

    cursor = Transaction().connection.cursor()
    table = ShipmentWork.__table__()

    shipment_works = ShipmentWork.search([])

    # relate shipment.work and project.work
    for sw in shipment_works:
        logger.info("sw: %s/%s" % (sw.number, sw.work_project))
        if not sw.work_project:
            continue
        project = Project.search([('name', '=', sw.work_project.code)])
        if project:
            project, = project
            logger.info("sw: %s/%s => %s" % (sw.number,
                sw.work_project.code, project))
            cursor.execute(*table.update(columns=[table.origin, table.project],
                values=['project.work,' + str(project.id), project.id],
                where=table.id == sw.id))
        else:
            cl = ContractLine.search([
                ('asset', '=', sw.asset),
                ('contract.party', '=', sw.party)])

            if not cl:
                continue
            cl = cl[0]
            logger.info("sw: %s/%s => %s" % (sw.number,
                sw.work_project.code, cl))
            cursor.execute(*table.update(columns=[table.origin],
                values=['contract.line,' + str(cl.id)],
                where=table.id == sw.id))

    # logger.info('Not null column project in shipment.work')
    # cursor.execute('ALTER TABLE "shipment_work" ALTER COLUMN "project"'
            # ' SET NOT NULL;')
    logger.info('Done')
