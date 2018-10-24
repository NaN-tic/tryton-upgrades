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

def get_tax(xml_id):
    pool = Pool()
    ModelData = pool.get('ir.model.data')
    AccountTax = pool.get('account.tax')
    AccountTaxTemplate = pool.get('account.tax.template')

    data, = ModelData.search([('module', '=', 'account_es'),
        ('fs_id', '=', xml_id)], limit=1)
    template = AccountTaxTemplate(data.db_id)
    # print("template:", template, template.name)
    with Transaction().set_context(active_test=False):
        tax, = AccountTax.search([('template', '=', template.id)], limit=1)
    return (template, tax)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

with Transaction().start(dbname, 0, context=context) as transaction:
    Module = pool.get('ir.module')

    cursor = Transaction().connection.cursor()
    cursor.execute('select * from mapping_taxes')

    xml_ids = {}
    parent_map = {}
    for x in cursor.fetchall():
        tax_id, name, parent, i347, fs_id, template_id, xml_id = x
        if '_' == xml_id[-1]:
            xml_id = xml_id[:-1]

        # print(xml_id, name, fs_id)
        new_template, new_tax = get_tax(xml_id)

        if xml_id in xml_ids:
            taxes, nt = xml_ids[xml_id]
            taxes.append(str(tax_id))
            xml_ids[xml_id] = (taxes, nt)
        else:
            xml_ids[xml_id] = ([str(tax_id)], new_tax.id)

        if parent in parent_map:
            parent_map[parent].append(new_tax.id)
        else:
            parent_map[parent] = [new_tax.id]

    tables = [
        ('account_invoice_tax', 'tax'),
        ('account_tax_line', 'tax')
    ]
    # print(xml_ids)
    for x in xml_ids:
        taxes, new_tax = xml_ids[x]
        for table, field in tables:
            cursor.execute(
                'update %s set %s = %s where tax in (%s)' % (
                    table, field, new_tax, ",".join(taxes)
                )
            )

    Transaction().connection.commit()

    tables2 = [('account_invoice_line_account_tax', 'tax')]
    sales = Module.search([
        ('name', '=', 'sale'),
        ('state', '=', 'activated')], limit=1)
    if sales:
        tables2.append(('sale_line_account_tax', 'tax'))
    purchases = Module.search([
        ('name', '=', 'purchase'),
        ('state', '=', 'activated')], limit=1)
    if purchases:
        tables2.append(('purchase_line_account_tax', 'tax'))

    for parent, taxes in parent_map.items():
        for table, field in tables2:
            cursor.execute('select id, line from %s where %s = %s' % (
                table, field, parent))

            for id_, line in cursor.fetchall():
                # cursor.execute('update %s set %s=%s where id=%s' % (
                #    table, field, taxes[0], id_))
                cursor.execute('delete from %s where id=%s'%(table, id_))
                for tax in taxes:
                    cursor.execute('insert into %s(tax,line) values(%s,%s)' % (
                        table, tax, line
                    ))

    Transaction().connection.commit()
