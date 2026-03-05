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
with Transaction().start(dbname, 0, context=context):

    pool = Pool()
    Template = pool.get('electronic.mail.template')
    User = pool.get('res.user')
    ActionReport = pool.get('ir.action.report')
    TemplateReport = pool.get('electronic.mail.template.ir.action.report')

    with Transaction().set_context(active_test=False):
        templates = Template.search([])

    for template in templates:
        if not template.reports:
            continue
        to_add = []
        to_remove = []
        for report in template.reports:
             if report.template_extension == 'jinja':
                    reports = ActionReport.search([
                        ('report_name', '=', report.report_name),
                        ('template_extension', '=', 'html'),
                        ], limit=1)
                    if reports:
                        report_dominate, = reports
                        to_add.append(report_dominate)
                        to_remove.append(report)
        if to_add or to_remove:
            updates = []
            if to_add:
                updates.append(('add', [r.id for r in to_add]))
            if to_remove:
                updates.append(('remove', [r.id for r in to_remove]))
            Template.write([template], {'reports': updates})

    Transaction().commit()
