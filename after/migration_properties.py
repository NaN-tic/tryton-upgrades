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

with Transaction().start(dbname, 0, context=context):
    Company = pool.get('company.company')
    Model = pool.get('ir.model')
    Field = pool.get('ir.model.field')

    cursor = Transaction().connection.cursor()

    models = Model.search([
        ('model', 'like', '%_configuration'),
        ])
    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            print("Company ID %s" % company.id)
            for model in models:
                ToSave = pool.get(model.model)
                toSave = ToSave(1)
                for field in Field.search([('model', '=', model)]):
                    if field.name in ['id', 'create_uid', 'create_date', 'write_uid', 'write_date']:
                        continue
                    query = 'select * from ir_property where field = %s and company = %s;' % (field.id, company.id)
                    cursor.execute(query)
                    results = cursor.fetchone()
                    if results:
                        value = results[5]
                        if not value:
                            continue
                        if field.ttype in ['many2many', 'one2many']:
                            continue
                        elif field.ttype == 'many2one':
                            model, _id = value.split(',')
                            ValueModel = pool.get(model)
                            valueModel = ValueModel(_id)
                            setattr(toSave, field.name, valueModel)
                        else:
                            if value.startswith(','):
                                setattr(toSave, field.name, value.split(',')[1])
                            else:
                                setattr(toSave, field.name, value)
                toSave.save()
    Transaction().commit()

    logger.info('Done')
