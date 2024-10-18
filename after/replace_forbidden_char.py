#!/usr/bin/env python
import os
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

from sql.functions import Function
from trytond.model import fields
# from psycopg2.errors import UndefinedColumn

class StringAgg(Function):
    __slots__ = ()
    _function = 'STRING_AGG'


with Transaction().start(dbname, 0, context=context):
    Model = pool.get('ir.model')
    ModelField = pool.get('ir.model.field')

    model_h = ModelField.__table__()
    model_field_h = ModelField.__table__()

    cursor = Transaction().connection.cursor()

    for field in ModelField.search([
            ('ttype', '=', 'char'),
            ('model.model', 'not like', 'babi_%'),
            ('model.model', 'not like', 'ir_%'),
            ]):
        Model = pool.get(field.model.model)
        try:
            table = Model.__table__()
        except AttributeError:
            continue

        column = field.name
        try:
            is_column = Model.__table_handler__().column_exist(column)
        except TypeError:
            continue
        if is_column:
            replace = "replace(replace( replace( replace(\""+column+"\", E'\\n', '' ), E'\n', '' ), E'\\t', '' ), E'\\r', '')"
            query = "UPDATE %(table)s set \"%(column)s\" = %(replace)s" % {'table': table, 'column': column, 'replace': replace}
            cursor.execute(query)

    # ir.translation
    for column in ('src', 'value'):
        replace = "replace(replace( replace( replace(\""+column+"\", E'\\n', '' ),  E'\n', '' ), E'\\t', '' ), E'\\r', '')"
        query = "UPDATE ir_translation set \"%(column)s\" = %(replace)s" % {'column': column, 'replace': replace}
        cursor.execute(query)

    Transaction().commit()

    logger.info('Done')
