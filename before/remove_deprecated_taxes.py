#!/usr/bin/env python
import sys
import psycopg2
from xml.dom.minidom import parse
import logging

database_name = sys.argv[1]

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

dom = parse('./modules/account_es/account.xml')
account_ids = []
for record in dom.getElementsByTagName('record'):
    if record.attributes['model'].value == 'account.account.template':
        account_ids.append(record.attributes['id'].value)

connection = psycopg2.connect(dbname=database_name)
cursor = connection.cursor()

tax_ids = ','.join("'%s'" % x for x in tax_ids)
query = ("SELECT fs_id, db_id FROM ir_model_data WHERE "
    "module='account_es' AND model='account.tax.template' AND "
    "fs_id NOT IN (%s)" % tax_ids)
cursor.execute(query)
records = cursor.fetchall()

template_ids = []
for record in records:
    fs_id = record[0]
    db_id = record[1]
    template_ids.append(str(db_id))

if template_ids:
    template_ids = ','.join(template_ids)
    query = ('UPDATE account_tax SET template = NULL, end_date=NOW()::DATE '
        'WHERE template IN (%s)' % template_ids)
    print('QUERY: ', query)
    cursor.execute(query)

connection.commit()
