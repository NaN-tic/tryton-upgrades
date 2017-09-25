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

    WorkProject = pool.get('work.project')
    WorkMilestone = pool.get('account.invoice.milestone')
    WorkMilestoneGroup = pool.get('account.invoice.milestone.group')
    Sale = pool.get('sale.sale')

    Milestone = pool.get('project.invoice_milestone')
    Project = pool.get('project.work')
    milestoneGroup = WorkMilestoneGroup.search([])

    trigger = {
        'confirmed_sale': 'start_project',
        'shipped_amount': 'progress',
        'sent_sale': 'finish_project',
    }

    states = {
        'draft': 'draft',
        'confirmed': 'confirmed',
        'processing': 'invoiced',
        'succeeded': 'invoiced',
        'failed':   'cancel',
        'cancel': 'cancel',
    }
    invoice_method = {
        'amount': 'fixed',
        'progress': 'progress',
        'sale_lines': 'progress',
        'shipped_goods': 'progress',
        'remainder': 'remainder',
    }

    projects = Project.search([('type', '=', 'project')])
    projects = dict((x.name, x) for x in projects)


    def get_project2(group):
        work_projects = list(set([x.work_project for x in group.sales if x]))
        project = None
        code = (work_projects and work_projects[0] != None and
            work_projects[0].code or None)
        project = projects.get(code, None)
        print "code:", code
        if not project:
            print "*"*10, "CHECK", "*"*10
            print "group:", group.code, "projects:", work_projects, code
        return project

    def get_project(group):
        projects = []
        for x in group.sales:
            projects += x.projects

        if len(projects) != 1:
            print "Check: %s projects for group %s " % \
                (",".join([x.name for x in projects]), group.code)

        if projects:
            return projects[0]

        # work_projects = list(set([x.work_project for x in group.sales if x]))
        # project = None
        # code = (work_projects and work_projects[0] != None and
        #     work_projects[0].code or None)
        # project = projects.get(code, None)
        # print "code:", code
        # if not project:
        #     print "*"*10, "CHECK", "*"*10
        #     print "group:", group.code, "projects:", work_projects, code
        # return project

    to_create = []
    invoiced_progress = []
    for group in milestoneGroup:
        project = get_project(group)
        print "project:", project, group.code
        if not project:
            continue
        InvoicedProgress = pool.get('project.work.invoiced_progress')

        for mil in group.milestones:
            milestone = Milestone()
            milestone.kind = mil.kind
            if mil.trigger:
                milestone.trigger = trigger[mil.trigger]
            if mil.trigger_shipped_amount:
                milestone.trigger_progress = mil.trigger_shipped_amount
            milestone.invoice_method = invoice_method[mil.invoice_method]
            milestone.advancement_product = mil.advancement_product
            milestone.compensation_product = mil.advancement_product
            milestone.advancement_amount = mil.amount
            milestone.currency = group.currency
            milestone.month = mil.month
            milestone.weeks = mil.weeks
            milestone.trigger_progress = mil.trigger_shipped_amount
            milestone.weekday = mil.weekday
            milestone.days = mil.days
            milestone.day = mil.day
            milestone.description = mil.description
            milestone.number = mil.code
            milestone.project = project
            milestone.invoice_date = mil.invoice_date
            milestone.planned_invoice_date = mil.planned_invoice_date
            milestone.processed_date = mil.processed_date
            milestone.invoice = mil.invoice
            milestone.state = states[mil.state]

            if mil.invoice and milestone.invoice_method == 'progress':
                for line in mil.invoice.lines:
                    ip = InvoicedProgress(work=project,
                        quantity=1, invoice_line=line)
                    invoiced_progress.append(ip)

            # TODO: CHECK this domain
            #       Check why invoice.party != project.party
            invoice_party = mil.invoice and mil.invoice.party
            if mil.invoice and (invoice_party != project.party):
                print "CHECK:", project.name, mil.invoice.number
            else:
                to_create.append(milestone)

    logger.info('Writing Milestones')
    Milestone.save(to_create)
    logger.info('%s Milestones created' % len(to_create))
    logger.info('Writing Invoiced Progress')
    InvoicedProgress.save(invoiced_progress)
    logger.info('%s Invoiced Progress created' % len(invoiced_progress))
