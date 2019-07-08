#!/usr/bin/env python
import sys
from xml.dom.minidom import parse

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.tools import grouped_slice
from trytond.transaction import Transaction
from trytond.pool import Pool
import logging

Pool.start()
pool = Pool(dbname)
pool.init()

context = {'active_test': True}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

dom = parse('./modules/account_es/tax.xml')
tax_ids = []
for record in dom.getElementsByTagName('record'):
    if record.attributes['model'].value == 'account.tax.template':
        tax_ids.append(record.attributes['id'].value)

with Transaction().start(dbname, 1, context=context) as transaction:
    Module = pool.get('ir.module')
    Company = pool.get('company.company')
    Data = pool.get('ir.model.data')

    cursor = Transaction().connection.cursor()

    taxes_data = dict((x.fs_id, x.db_id) for x in Data.search([
                ('module', '=', 'account_es'),
                ('model', '=', 'account.tax.template'),
                ('fs_id', 'not in', tax_ids),
                ]))

    print('Not found: %s' % taxes_data.keys())

    import sys
    sys.exit(1)

    tax_to_check_ids = []
    template_to_remove = []
    data_to_remove = []
    for k, data in taxes_data.items():
        if k in tax_ids:
            continue

        tax_template_id = data.db_id
        cursor.execute('select id from account_tax where template = %s' % (tax_template_id))
        taxids = [id[0] for id in cursor.fetchall()]
        if taxids:
            tax_to_check_ids += taxids
        template_to_remove.append(tax_template_id)
        data_to_remove.append(data.id)

    ids_ = ', '.join(str(t) for t in tax_to_check_ids)
    if not ids_:
        sys.exit()

    tax_ids = set()
    for table in tables:
        table_name = table[0]
        table_field = table[1]
        # print(table_name)
        cursor.execute('select %s from %s where %s in (%s) group by %s' % (table_field, table_name, table_field, ids_, table_field))
        tax_ids |= set([id[0] for id in cursor.fetchall()])

    tax_to_remove = []
    tax_to_null = []
    for tax_id in tax_to_check_ids:
        if tax_id in tax_ids:
            tax_to_null.append(tax_id)
        else:
            tax_to_remove.append(tax_id)

    if tax_to_null:
        print('TAX to null: %s' % len(tax_to_null))
        for sub_ids in grouped_slice(tax_to_null, 250):
            query = 'update account_tax set template = null where id in (%s)' % (', '.join(str(t) for t in list(sub_ids)))
            cursor.execute(query)
            Transaction().connection.commit()
    if tax_to_remove:
        print('TAX to remove: %s' % len(tax_to_remove))
        for sub_ids in grouped_slice(tax_to_remove, 250):
            tax_ids = ', '.join(str(t) for t in list(sub_ids))
            query = 'delete FROM account_tax_rule_line where tax in (%s)' % (tax_ids)
            # print(query)
            cursor.execute(query)
            query = 'delete FROM account_tax_rule_line where origin_tax in (%s)' % (tax_ids)
            # print(query)
            cursor.execute(query)
            query = 'delete from account_tax where id in (%s)' % (tax_ids)
            # print(query)
            cursor.execute(query)
            Transaction().connection.commit()
    if template_to_remove:
        print('TAX template to remove: %s' % len(template_to_remove))
        for sub_ids in grouped_slice(template_to_remove, 250):
            tax_ids = ', '.join(str(t) for t in list(sub_ids))
            query = 'delete FROM account_tax_rule_line_template where tax in (%s)' % (tax_ids)
            # print(query)
            cursor.execute(query)
            query = 'delete FROM account_tax_rule_line_template where origin_tax in (%s)' % (tax_ids)
            # print(query)
            cursor.execute(query)
            query = 'delete from account_tax_template where id in (%s)' % (tax_ids)
            # print(query)
            cursor.execute(query)
            Transaction().connection.commit()
    if data_to_remove:
        print('Data to remove: %s' % len(data_to_remove))
        for sub_ids in grouped_slice(data_to_remove, 250):
            query = 'delete from ir_model_data where id in (%s)' % (', '.join(str(t) for t in list(sub_ids)))
            # print(query)
            cursor.execute(query)
            Transaction().connection.commit()

    Transaction().connection.commit()
