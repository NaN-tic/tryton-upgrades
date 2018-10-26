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
    Company = pool.get('company.company')
    ModelData = pool.get('ir.model.data')
    Category = pool.get('product.category')
    Template = pool.get('product.template')
    Account = pool.get('account.account')
    Tax = pool.get('account.tax')

    cursor = Transaction().cursor

    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            mdata_expense, = ModelData.search([('fs_id', '=', 'pgc_600_child')], limit=1)
            mdata_revenue, = ModelData.search([('fs_id', '=', 'pgc_7000_child')], limit=1)
            mdata_customer_tax, = ModelData.search([('fs_id', '=', 'iva_rep_21')], limit=1)
            mdata_supplier_tax, = ModelData.search([('fs_id', '=', 'iva_sop_21')], limit=1)

            categories = dict((
                (c.account_expense_used, c.account_revenue_used, c.customer_taxes_used, c.supplier_taxes_used), c) for c in Category.search([('accounting', '=', True)]))

            expense, = Account.search([('template', '=', mdata_expense.db_id)], limit=1)
            revenue, = Account.search([('template', '=', mdata_revenue.db_id)], limit=1)
            customer_tax, = Tax.search([('template', '=', mdata_customer_tax.db_id)], limit=1)
            supplier_tax, = Tax.search([('template', '=', mdata_supplier_tax.db_id)], limit=1)

            to_write = []
            with Transaction().set_context(active_test=False):
                for template in Template.search([]):
                    try:
                        account_expense_used = template.account_expense_used
                    except:
                        account_expense_used = expense
                    if not account_expense_used:
                        account_expense_used = expense
                    try:
                        account_revenue_used = template.account_revenue_used
                    except:
                        account_revenue_used = revenue
                    if not account_revenue_used:
                        account_revenue_used = revenue
                    try:
                        customer_taxes_used = template.customer_taxes_used
                    except:
                        customer_taxes_used = (customer_tax,)
                    if not customer_taxes_used:
                        customer_taxes_used = (customer_tax,)
                    try:
                        supplier_taxes_used = template.supplier_taxes_used
                    except:
                        supplier_taxes_used = (supplier_tax,)
                    if not supplier_taxes_used:
                        supplier_taxes_used = (supplier_tax,)

                    key = (account_expense_used, account_revenue_used, customer_taxes_used, supplier_taxes_used)
                    if not categories.get(key):
                        category = Category()
                        category.name = '%s | %s | %s | %s' % (account_expense_used.rec_name, account_revenue_used.rec_name, ','.join(t.rec_name for t in customer_taxes_used), ','.join(t.rec_name for t in supplier_taxes_used))
                        category.accounting = True
                        category.account_expense = account_expense_used
                        category.account_revenue = account_revenue_used
                        category.customer_taxes = customer_taxes_used
                        category.supplier_taxes = supplier_taxes_used
                        category.save()
                        categories[key] = category

                    to_write.extend(([template], {
                        'account_category_migration': categories[key],
                        'account_expense': None,
                        'account_revenue': None,
                        'taxes_category': True,
                        'account_category': True,
                        }))

            logger.info('%s: Upgrading Account Products' % (company.rec_name))

            if to_write:
                Template.write(*to_write)

            logger.info('%s: Upgrading Account Categories' % (company.rec_name))

            for category in Category.search([('accounting', '=', False)]):
                category.account_expense = None
                category.account_revenue = None
                category.save()

    query = "DROP TABLE if exists product_customer_taxes_rel;"
    cursor.execute(query)
    query = "DROP TABLE if exists product_supplier_taxes_rel;"
    cursor.execute(query)
    # query = "DROP TABLE if exists product_category_customer_taxes_rel;"
    # cursor.execute(query)
    # query = "DROP TABLE if exists product_category_supplier_taxes_rel;"
    # cursor.execute(query)

    Transaction().cursor.commit()

    logger.info('Done')
