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


    query = 'SELECT * FROM pg_catalog.pg_tables'
    cursor.execute(query)
    tables = [name for _, name, _, _, _, _, _, _ in cursor.fetchall()]

    sql_where = (model_field_h.ttype == 'char')
    query = model_field_h.select(model_field_h.model, StringAgg(model_field_h.name, ','), group_by=model_field_h.model, where=sql_where)
    cursor.execute(*query)

    for model_id, model_fields in cursor.fetchall():
        model = Model(model_id)
        ModelRecord = pool.get(model.model)

        if not hasattr(ModelRecord, '_table') or hasattr(ModelRecord, 'table_query'):
            continue

        table = ModelRecord._table
        if table.startswith(('babi_', 'ir')) or table not in tables:
            continue

        model_h = ModelRecord.__table__()
        field_names = model_fields.split(',')

        to_write = []
        for _field, _ttype in ModelRecord._fields.items():
            if _field in field_names and not isinstance(_ttype, fields.Function):
                to_write.append(_field)

        if to_write:
            columns = ', '.join([column+" = replace( replace( replace("+column+", E'\\n', '' ), E'\\t', '' ), E'\\r', '')" for column in to_write])
            query = "UPDATE %(table)s set %(columns)s" % {'table': table, 'columns': columns}
            # print(query)
            cursor.execute(query)

    Transaction().commit()

    logger.info('Done')
