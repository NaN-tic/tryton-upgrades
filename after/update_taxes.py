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


#TODO: tax.rule
#TODO: account.move.template

context = {}

def get_tax(xml_id, company):
    pool = Pool()
    ModelData = pool.get('ir.model.data')
    AccountTax = pool.get('account.tax')
    AccountTaxTemplate = pool.get('account.tax.template')

    if xml_id[-3:] == '_re':
        xml_id = xml_id.replace('_re','')
    data = ModelData.search([('module', '=', 'account_es'),
        ('fs_id', '=', xml_id)], limit=1)
    if not data:
        return (None, None)
    data, = data
    template = AccountTaxTemplate(data.db_id)
    with Transaction().set_context(): #active_test=False):
        tax = AccountTax.search([
            ('template', '=', template.id),
            ('company', '=', company)], limit=1)
        if tax:
            tax, = tax
        else:
            None
    return (template, tax)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

with Transaction().start(dbname, 1, context=context) as transaction:
    Module = pool.get('ir.module')
    Company = pool.get('company.company')

    cursor = Transaction().connection.cursor()
    cursor.execute('select * from mapping_taxes')

    domain = []
    child_companies = Company.search([('parent', '!=', None)])
    if child_companies:
        domain.append(('parent', '!=', None))

    for company in Company.search(domain):
        logger.info("company %s" % company.id)
        with Transaction().set_context(company=company.id):
            cursor.execute("""
            select mt.tax_id,
                mt.tax_name,
                mt.tax_parent,
                mt.include_347,
                mt.fs_id,
                mt.template_id,
                mt.parent_template,
                mt.split_part
            from mapping_taxes as mt
                left join account_tax as at on at.id = mt.tax_id
                 where at.company = %s
                 """% str(company.id))

            xml_ids = {}
            parent_map = {}
            template_map = {}
            for x in cursor.fetchall():
                tax_id, name, parent, i347, fs_id, template_id, parent_template, xml_id = x
                # print(name, xml_id, parent_template, template_id, fs_id)
                # import pdb; pdb.set_trace()

                if '_' == xml_id[-1]:
                    xml_id = xml_id[:-1]

                new_template, new_tax = get_tax(xml_id, company.id)

                if not new_tax:
                    continue
                if not new_template:
                    continue

                # print("xml_id:", xml_id, new_template.name, new_tax.name)
                if xml_id in xml_ids:
                    taxes, nt = xml_ids[xml_id]
                    taxes.append(str(tax_id))
                    xml_ids[xml_id] = (taxes, nt)
                else:
                    xml_ids[xml_id] = ([str(tax_id)], new_tax.id)

                if parent in parent_map:
                    if not new_template.id in template_map[parent_template]:
                        template_map[parent_template].append(new_template.id)
                    if not (new_tax.id, new_template.id) in parent_map[parent]:
                        parent_map[parent].append((new_tax.id, new_template.id))
                else:
                    template_map[parent_template] = [new_template.id]
                    parent_map[parent] = [(new_tax.id, new_template.id)]

            tables = [
                ('account_invoice_tax', 'tax'),
                ('account_tax_line', 'tax')
            ]
            for x in xml_ids:
                taxes, new_tax = xml_ids[x]
                for table, field in tables:
                    # print('update %s set %s = %s where tax in (%s)' % (
                    #       table, field, new_tax, ",".join(taxes)))
                    cursor.execute(
                     'update %s set %s = %s where tax in (%s)' % (
                         table, field, new_tax, ",".join(taxes)
                      )
                    )
            Transaction().connection.commit()
            tables2 = [
                ('account_invoice_line_account_tax', 'tax', 'line' ),
                ('product_category_customer_taxes_rel', 'tax', 'category'),
            ]

            sales = Module.search([
                ('name', '=', 'sale'),
                ('state', '=', 'activated')], limit=1)
            if sales:
                tables2.append(('sale_line_account_tax', 'tax', 'line'))
            purchases = Module.search([
                ('name', '=', 'purchase'),
                ('state', '=', 'activated')], limit=1)
            if purchases:
                tables2.append(('purchase_line_account_tax', 'tax', 'line'))

            for parent, taxes in parent_map.items():
                for table, field, rel in tables2:
                    cursor.execute('select id, %s from %s where %s = %s' % (
                        rel, table, field, parent))

                    for id_, line in cursor.fetchall():
                        cursor.execute('delete from %s where id=%s'%(table, id_))
                        for tax, template in taxes:
                            cursor.execute('insert into %s(tax,%s) values(%s,%s)' % (
                                table, rel, tax, line
                            ))

            account_template_product = Module.search([
                ('name', '=', 'account_template_product'),
                ('state', '=', 'activated')], limit=1)
            if account_template_product:
                tables3 = [
                    ('product_customer_taxes_template_rel', 'tax', 'product'),
                    ('product_category_customer_taxes_template_rel', 'tax', 'product')
                ]

                for template, taxes in template_map.items():
                    for table, field, rel in tables3:
                        cursor.execute('select id, %s from %s where %s = %s' % (
                            rel, table, field, template))

                        for id_, line in cursor.fetchall():
                            cursor.execute('delete from %s where id=%s'%(table, id_))
                            for tax in taxes:
                                cursor.execute('insert into %s(tax,%s) values(%s,%s)' % (
                                    table, rel, tax, line
                                ))
        Transaction().connection.commit()
