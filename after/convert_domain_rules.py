#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]
from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction
from trytond.pool import Pool
import logging
from trytond.pyson import PYSONEncoder, Eval

# Avoid pyflakes warnings and use Eval which may be needed by 'eval()'
Eval

Pool.start()
pool = Pool(dbname)
pool.init()

context = {'company': 1}

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


with Transaction().start(dbname, 0, context=context) as transaction:

    pool = Pool()
    Rule = pool.get('ir.rule.group')

    groups = Rule.search([('create_uid', '>', 0)])
    for group in groups:
        for rule in group.rules:
            rule.domain = PYSONEncoder().encode(eval(rule.domain))
            rule.save()


with Transaction().start(dbname, 0, context=context) as transaction:

    pool = Pool()
    ActWindow = pool.get('ir.action.act_window')

    actions = ActWindow.search([])
    for action in actions:

        if action.domain and 'null' in action.domain:
            action.domain = action.domain.replace('null', "None")
        if action.context and 'true' in action.context:
            action.context = action.context.replace('true', "True")
        if action.domain:
            domain = action.domain.replace('null', 'None').replace(
                'true', 'True').replace('false', 'False')
            action.domain = PYSONEncoder().encode(eval(domain, {'Eval': Eval}))
        if action.context:
            context_ = action.context.replace('null', 'None').replace('true',
                'True').replace('false', 'False')
            action.context = PYSONEncoder().encode(eval(context_, {}))
        action.save()

with Transaction().start(dbname, 0, context=context) as transaction:

    pool = Pool()
    ActWindowDomain = pool.get('ir.action.act_window.domain')

    actions = ActWindowDomain.search([('create_uid', '>', 0)])
    for action in actions:
        if not action.domain or action.domain.strip() == '':
            continue
        action.domain = PYSONEncoder().encode(eval(action.domain))
        action.save()

with Transaction().start(dbname, 0, context=context) as transaction:

    pool = Pool()
    Trigger = pool.get('ir.trigger')
    triggers = Trigger.search([])
    for trigger in triggers:
        print("Update Manaualy:", trigger.id, trigger.condition)
        if not trigger.condition and trigger.condition.strip() == '':
            continue
        trigger.condition = PYSONEncoder().encode(eval(trigger.condition))
        trigger.save()
