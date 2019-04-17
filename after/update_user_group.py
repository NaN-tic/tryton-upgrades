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


with Transaction().start(dbname, 1, context=context) as transaction:
    Module = pool.get('ir.module')
    Company = pool.get('company.company')

    User = Pool().get('res.user')
    UserGroup = Pool().get('res.user-res.group')
    Group = Pool().get('res.group')

    users = User.search([])

    #franchise_group, =  Group.search([('name','=', 'Franchise Account Tax')])
    main_group, =  Group.search([('name','=', 'Fruites Montbui Account Tax')])
    for user in users:
        if user.company and user.company.id != 14:
            continue

        ug = UserGroup()
        ug.user = user
        ug.group = main_group
        ug.save()
