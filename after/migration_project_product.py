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
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s'
    '- %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

with Transaction().start(dbname, 0, context=context):
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id

with Transaction().start(dbname, 0, context=context) as transaction:

    WorkProject = pool.get('work.project')
    Project = pool.get('project.work')
    Category = pool.get('sale.opportunity.category')
#    Certification = pool.get('project.certification')
#    CertificationLine = pool.get('project.certification.line')
    Sale = pool.get('sale.sale')
    SaleLine = pool.get('sale.line')

    Product = pool.get('product.product')
    Template = pool.get('product.template')
    Uom = pool.get('product.uom')
    unit, = Uom.search([
            ('name', '=', 'Unit'),
            ])

    product, = Product.search([('type', '=', 'goods')], limit=1)
    template = Template()
    template.name = 'Projectes'
    template.list_price = 0
    template.cost_price = 0
    template.default_uom = unit
    template.sale_uom = unit
    template.purchase_uom = unit
    template.type = 'goods'
    template.account_category = product.account_category
    template.save()

    p = Product(template=template, code='PROJECTES')
    p.save()

    work_projects = WorkProject.search([])
    work_project = dict((x.code, x) for x in work_projects)
    projects = []
    default_category = Category(name='Per Configurar')
    logger.info('Start reading projects')

    for wp in work_projects:
        if wp.contract_lines:
            continue
        project = Project()
        project.invoice_product_type = 'goods'
        project.product_goods = product
        project.uom = product.default_uom
        project.project_invoice_method = 'milestone'
        project.name = wp.code
        project.type = 'project'
        project.company = wp.company
        project.party = wp.party
        project.state = 'draft' #TODO
        project.note = wp.note
        project.asset = wp.asset
    #    project.category = wp.category or default_category
        project.children = []
        project.quantity = 1
        project.progress_quantity = 0
        project.start_date = wp.start_date
        # project.parent = None
        #project.end_date = wp.end_date
        # wp.maintenance =
        projects.append(project)
    #    print project._save_values
        #    project.save()


    logger.info('Writing projects')
    #Project.create([x._save_values for x in projects])
    Project.save(projects)
    logger.info('%s projects createds' % len(projects))

    transaction.commit()

    logger.info('Start upload Tasks')
    projects = Project.search([])
    tasks = []
    sales = []

    cursor = Transaction().connection.cursor()
    table_sale_line = SaleLine.__table__()
    table_sale = Sale.__table__()

    to_create = []
    for project in projects:
        wp = work_project[project.name]
        childs = {}
        for sale in wp.sales:
            sale.work = project
            # Update parent_project Sale
            cursor.execute(*table_sale.update(columns=
                [table_sale.parent_project],
                values=[project.id],
                where=table_sale.id == sale.id))

            if sale.state in ('draft', 'cancel'):
                continue

            p2 = Project()
            p2.invoice_product_type = 'goods'
            p2.product_goods = product
            p2.uom = product.default_uom
            p2.project_invoice_method = 'milestone'
            p2.name = sale.number
            p2.type = 'project'
            p2.company = sale.company
            p2.party = sale.party
            p2.state = 'draft'
            p2.note = wp.note
            p2.asset = wp.asset  # TODO: Problemes with domains
            # p2.category = wp.category or default_category
            p2.children = []
            p2.quantity = 1
            p2.progress_quantity = 0
            p2.start_date = sale.sale_date
            p2.parent = project
            to_create.append(p2)

    logger.info('Writing projects %s' % len(to_create))
    offset = 1000
    i = 0
    while i < len(to_create):
        logger.info('Writing projects %s-%s/%s' %
            (i, i+offset, len(to_create)))
        create = to_create[i:i + offset]
        Project.save(create)
        i += offset
        i = min(i, len(to_create))
        logger.info('Projects createds')

    # Update All sale lines with project created
    cursor.execute(
        "update sale_line l set project = project_id FROM "
        "( "
        "select s.id as sale, l.id, number, p.id as project_id "
        "   from sale_sale s, "
        "        sale_line l,"
        "        project_work p "
        " where s.id = l.sale and "
        "       s.number = p.name "
        ") as sub "
        "where l.sale = sub.sale"
    )

    transaction.commit()
