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

with Transaction().start(dbname, 0, context=context) as transaction:
    ModelData = pool.get('ir.model.data')
    Menu = pool.get('ir.ui.menu')
    Action = pool.get('ir.action')
    ActWindow = pool.get('ir.action.act_window')
    ActionKeyword = pool.get('ir.action.keyword')
    ActWindowView = pool.get('ir.action.act_window.view')
    View = pool.get('ir.ui.view')
    Mailbox = pool.get('electronic.mail.mailbox')

    act_windows = []
    actions = []
    keywords = []
    menus = []
    act_window_views = []
    for mailbox in Mailbox.search([]):
        act_windows = ActWindow.search([
                ('res_model', '=', 'electronic.mail'),
                ('domain', '=', '[["mailbox", "=", %d]]' % mailbox.id),
                ])
        actions = [a_w.action for a_w in act_windows]
        keywords = ActionKeyword.search([('action', 'in', actions)])
        menus = [k.model for k in keywords]
        if menus:
            # sure that menu is not from xml data
            datas = ModelData.search([
                    # ('module', '=', 'electronic_mail'),
                    ('model', '=', 'ir.ui.menu'),
                    # ('fs_id', '=', 'menu_mail'),
                    ('db_id', 'in', [m.id for m in menus]),
                    ])
            if datas:
                continue

        act_windows.extend(ActWindow.search([
                ('res_model', '=', 'electronic.mail'),
                ('domain', '=', '[["mailbox", "=", %d]]' % mailbox.id),
                ]))
        actions.extend([a_w.action for a_w in act_windows])
        keywords.extend(ActionKeyword.search([('action', 'in', actions)]))
        menus.extend([k.model for k in keywords])
        act_window_views.extend(ActWindowView.search([
                ('act_window', 'in', [a_w.id for a_w in act_windows]),
                ]))

    ActWindowView.delete(act_window_views)
    ActWindow.delete(act_windows)
    ActionKeyword.delete(keywords)
    Action.delete(actions)
    Menu.delete(menus)

    transaction.commit()
