#!/usr/bin/env python
import sys
from trytond.transaction import Transaction
from trytond.config import config as CONFIG

dbname = sys.argv[1]
config_file = sys.argv[2]

CONFIG.update_etc(config_file)

context = {}


def execute(query, *args, **kwargs):
    if not args:
        args = kwargs
    cursor.execute(query, args)


def field_exists(field):
    table, field = field.split('.')
    execute('SELECT count(*) FROM information_schema.columns '
        'WHERE table_name=%s AND column_name=%s', table, field)
    return bool(cursor.fetchone()[0])


with Transaction().start(dbname, 1, context=context) as transaction:
    price_decimal = CONFIG.get('product', 'price_decimal')
    if price_decimal and field_exists('ir_configuration.product_price_decimal'):
        cursor = Transaction().connection.cursor()
        cursor.execute('UPDATE ir_configuration SET product_price_decimal = ' + str(price_decimal))
        transaction.commit()
