#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
from datetime import timedelta
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

def get_property_value(field_name, company_id, default=True):
    query = """
        select
               p.value
        from ir_property_backup p,
            ir_model_field f
        where p.field = f.id
          and f.name = '%s'
    """ % (field_name)
    if default:
        query += ' and res is null'
    if company_id:
        query += " and company = %s" % company_id
    else:
        query += " and company is null"
    cursor = Transaction().connection.cursor()
    cursor.execute(query)
    results = cursor.fetchone()

    result = results and results[0]
    if not result:
        return

    return result.split(',')[1]

def account_configuration():
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id

    try:
        Company = pool.get('company.company')
        AccountConfiguration = pool.get('account.configuration')
        Account = pool.get('account.account')
        Sequence = pool.get('ir.sequence')
        SequenceType = pool.get('ir.sequence_type')
    except KeyError:
        return

    mapping = {
        'account_receivable': 'default_account_receivable',
        'account_payable': 'default_account_payable',
        'account_expense': 'default_product_account_expense',
        'account_revenue': 'default_product_account_revenue',
        }

    domain=[]

    for company in Company.search(domain):
        logger.info("company %s" % company.id)
        user.companies += (company,)
        user.company = company.id
        user.save()
        with Transaction().set_context(company=company.id):
            print("company:", company.id)
            accountConfig = AccountConfiguration(1)
            for field in ('account_receivable', 'account_payable',
                    'account_expense', 'account_revenue'):
                value = get_property_value(field, company.id)

                if not value:
                    continue

                # Given property's weak consistency, the account set as default
                # may no longer exist
                accounts = Account.search([('id', '=', int(value))], limit=1)
                if not accounts:
                    continue
                a, = accounts
                print("Account:", field, value, a.code, a.type.receivable, a.type.payable)
                if 'receivable' in field and not a.type.receivable:
                    a.type.receivable = True
                    a.type.save()
                if 'payable' in field and not a.type.payable:
                    a.type.payable = True
                    a.type.save()
                setattr(accountConfig, mapping[field], int(value))

            asset_sequence_type = SequenceType.search([
                ('code', '=', 'account.asset')
            ], limit=1)

            asset_sequence = None
            asset_sequence2 = None
            if asset_sequence_type:
                asset_sequence = Sequence.search([
                    ('sequence_type', '=', asset_sequence_type[0]),
                    ('company', '=', company.id)])
                asset_sequence2 = Sequence.search([
                    ('sequence_type', '=', asset_sequence_type[0]),
                    ('company', '=', None)])
            if asset_sequence:
                accountConfig.asset_sequence = asset_sequence[0]
            elif asset_sequence2:
                accountConfig.asset_sequence = asset_sequence2[0]

            accountConfig.save()
            Transaction().commit()

def party_configuration():
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id
    try:
        Company = pool.get('company.company')
        PartyConfiguration = pool.get('party.configuration')
    except KeyError:
        return
    mapping = {
        'party_lang': 'party_lang',
        }
    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            partyConfig = PartyConfiguration(1)
            for field in ('party_lang', ):
                value = get_property_value(field, company.id, default=False)
                if not value:
                    continue
            if not value is None:
                setattr(partyConfig, mapping[field], int(value))
        partyConfig.save()
        Transaction().commit()

def sale_configuration():
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id
    mapping = {
        'sale_invoice_method': 'sale_invoice_method',
        'sale_shipment_method': 'sale_shipment_method',
        'sale_sequence': 'sale_sequence'
        }
    try:
        Company = pool.get('company.company')
        SaleConfiguration = pool.get('sale.configuration')
    except KeyError:
        return
    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            saleConfig = SaleConfiguration(1)
            for field in mapping.keys():
                value = get_property_value(field, company.id, default=False)
                if not value:
                    continue
                if field == 'sale_sequence':
                    value = int(value)
                print("Sale:", field, value)
                setattr(saleConfig, mapping[field], value)
        saleConfig.save()
        Transaction().commit()


def stock_configuration():
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id
    try:
        Company = pool.get('company.company')
        StockConfiguration = pool.get('stock.configuration')
    except KeyError:
        return
    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            stockConfig = StockConfiguration(1)
            try:
                stockConfig.valued_origin = True
            except AttributeError:
                pass
        stockConfig.save()
        Transaction().commit()


def purchase_configuration():
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id
    try:
        Company = pool.get('company.company')
        PurchaseConfiguration = pool.get('purchase.configuration')
    except KeyError:
        return
    mapping = {
        'purchase_invoice_method': 'purchase_invoice_method',
        'supply_period': 'supply_period',
        'purchase_sequence': 'purchase_sequence'
        }
    for company in Company.search([]):
        with Transaction().set_context(company=company.id):
            purchaseConfig = PurchaseConfiguration(1)
            for field in mapping.keys():
                value = get_property_value(field, company.id, default=False)
                if not value:
                    continue
                if field == 'supply_period':
                    value = timedelta(days=eval(value))
                if field == 'purchase_sequence':
                    value = int(value)
                print("Purchae:", field, value)
                setattr(purchaseConfig, mapping[field], value)
        purchaseConfig.save()
        Transaction().commit()


with Transaction().start(dbname, 0, context=context):
    account_configuration()
    Transaction().commit()

with Transaction().start(dbname, 0, context=context):
    party_configuration()
    Transaction().commit()

with Transaction().start(dbname, 0, context=context):
    sale_configuration()
    Transaction().commit()

with Transaction().start(dbname, 0, context=context):
    stock_configuration()
    Transaction().commit()

with Transaction().start(dbname, 0, context=context):
    purchase_configuration()
    Transaction().commit()


logger.info('Done')
