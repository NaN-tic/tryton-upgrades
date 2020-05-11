#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)
from decimal import Decimal
from trytond.pool import Pool
from trytond.transaction import Transaction

Pool.start()
pool = Pool(dbname)
pool.init()


context = {}

with Transaction().start(dbname, 1, context=context) as transaction:
    Module = pool.get('ir.module')
    Company = pool.get('company.company')
    Party = pool.get('party.party')

    cursor = Transaction().connection.cursor()
    cursor.execute('''
        select f.id ,
            f.name,
            p.res,
            p.value,
            p.company
        from ir_model_field f,
            ir_model m, ir_property p
        where f.module='account_invoice_discount_global' and
            f.model=m.id and m.name ='Party'
            and p.field = f.id
            order by p.company
    ''')

    for fid,fname,res,value,company in cursor.fetchall():
        with Transaction().set_context(company=company):
            party_id = res.split(',')[1]
            party = Party(party_id)
            setattr(party, fname, Decimal(str(value.replace(',',''))))
            party.save()
