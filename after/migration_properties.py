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

def get_property_value(field_name, company_id):
        query = """
            select
        	   p.value
            from ir_property_backup p,
                ir_model_field f
            where p.field = f.id
              and f.name = '%s'
              and res is null
        """ % (field_name)
        if company_id:
            query += " and company = %s" % company_id
        else:
            query += " and company is null"
        cursor.execute(query)
        results = cursor.fetchone()
        result = results and results[0]
        if not result:
            return
        return int(result.split(',')[1])

# Change account_configuration
with Transaction().start(dbname, 0, context=context):
    Company = pool.get('company.company')
    Model = pool.get('ir.model')
    Field = pool.get('ir.model.field')
    AccountConfiguration = pool.get('account.configuration')
    Account = pool.get('account.account')
    Sequence = pool.get('ir.sequence')

    cursor = Transaction().connection.cursor()
    mapping = {
        'account_receivable': 'default_account_receivable',
        'account_payable': 'default_account_payable',
        'account_expense': 'default_product_account_expense',
        'account_revenue': 'default_product_account_revenue',
    }

    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            print "Company ID %s" % company.id
            accountConfig = AccountConfiguration(1)
            for field in ('account_receivable', 'account_payable',
                    'account_expense', 'account_revenue'):
                value = get_property_value(field, company.id)
                if not value:
                    continue
                setattr(accountConfig, mapping[field], value)

            asset_sequence = Sequence.search([
                ('code','=', 'account.asset'), ('company', '=', company.id)])
            asset_sequence2 = Sequence.search([
                ('code','=', 'account.asset'), ('company', '=', None)])
            if asset_sequence:
                accountConfig.asset_sequence = asset_sequence[0]
            else:
                accountConfig.asset_sequence = asset_sequence2[0]

            accountConfig.save()
        Transaction().commit()

# with Transaction().start(dbname, 0, context=context):
#     Company = pool.get('company.company')
#     Model = pool.get('ir.model')
#     Field = pool.get('ir.model.field')
#
#     cursor = Transaction().connection.cursor()
#
#     models = Model.search([
#         ('model', 'like', '%_configuration'),
#         ])
#     for company in Company.search([]):
#         with Transaction().set_context(company=company.id):
#             save = {}
#             for model in models:
#                 try:
#                     ToSave = pool.get(model.model)
#                 except:
#                     continue
#                 if model in save:
#                     to_save = save[model]
#                 else:
#                     toSave = ToSave(1)
#                     save[model] = toSave
#                 for field in Field.search([('model', '=', model)]):
#                     if field.name in ['id', 'create_uid', 'create_date', 'write_uid', 'write_date']:
#                         continue
#                     query = 'select * from ir_property where field = %s and company = %s;' % (field.id, company.id)
#                     cursor.execute(query)
#                     results = cursor.fetchone()
#                     if results:
#                         value = results[5]
#                         if field.ttype in ['many2many', 'one2many']:
#                             continue
#                         elif field.ttype == 'many2one' and value:
#                             model, _id = value.split(',')
#                             ValueModel = pool.get(model)
#                             valueModel = ValueModel(_id)
#                             setattr(toSave, field.name, valueModel)
#                         else:
#                             if value and value.startswith(','):
#                                 setattr(toSave, field.name, value.split(',')[1])
#                             else:
#                                 setattr(toSave, field.name, value)
#             for model, toSave in save.items():
#                 toSave.save()
#     Transaction().commit()

    logger.info('Done')
