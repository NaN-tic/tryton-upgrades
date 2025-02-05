#!/usr/bin/env python
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

model_startswiths = {
    'sale': 'group_sale',
    'stock': 'group_stock',
    'purchase': 'group_purchase',
    'account': 'group_account',
    'production': 'group_production',
    }

with Transaction().start(dbname, 0, context=context) as transaction:
    Button = pool.get('ir.model.button')
    ModelData = pool.get('ir.model.data')
    UserGroup = pool.get('res.group')
    Menu = pool.get('ir.ui.menu')
    ActionWindow = pool.get('ir.action.act_window')

    # buttons
    for button in Button.search([('groups', '!=', None)]):
        modules = [module for module in model_startswiths.keys() if button.model.startswith(module)]
        if not modules:
            continue

        module = modules[0]
        fs_id = model_startswiths.get(module)
        if not fs_id:
            continue

        btn_cores = ModelData.search([
            ('model', '=',  'res.group'),
            ('db_id', 'in', [g.id for g in button.groups]),
            ])
        # in case has only a core group, not add new groups
        if len(btn_cores) == 1 and len(button.groups) == 1:
            continue

        default_group = UserGroup(ModelData.get_id(module, fs_id))
        groups = button.groups
        if default_group in button.groups:
            continue
        button.groups += (default_group,)
        button.save()

    # menus
    for menu in Menu.search([('groups', '!=', None)]):
        if isinstance(menu.action, ActionWindow):
            modules = [module for module in model_startswiths.keys() if menu.action.res_model and menu.action.res_model.startswith(module)]
            if not modules:
                continue

            module = modules[0]
            fs_id = model_startswiths.get(module)
            if not fs_id:
                continue

            menu_cores = ModelData.search([
                ('model', '=',  'res.group'),
                ('db_id', 'in', [g.id for g in menu.groups]),
                ])
            # in case has only a core group, not add new groups
            if len(menu_cores) == 1 and len(menu.groups) == 1:
                continue

            default_group = UserGroup(ModelData.get_id(module, fs_id))
            groups = menu.groups
            if default_group in menu.groups:
                continue
            menu.groups += (default_group,)
            menu.save()

    transaction.commit()
