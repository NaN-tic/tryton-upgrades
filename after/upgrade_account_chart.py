#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
digits = int(os.environ['upgrade_account_chart_digits'])
domain = os.environ.get('upgrade_account_chart_domain')
if domain:
    domain = eval(domain)

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


with Transaction().start(dbname, 1, context=context):
    Company = pool.get('company.company')
    ModelData = pool.get('ir.model.data')
    Configuration = pool.get('account.configuration')
    Account = pool.get('account.account')
    AccountTemplate = pool.get('account.account.template')
    Party = pool.get('party.party')

    party = Party.search([('name', '=', 'Generic for Party required Accounts')])
    if not party:
        party = Party(name='Generic for Party required Accounts', code='GPRA')
        party.save()
    else:
        party, = party

    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id

    cursor = Transaction().connection.cursor()

    to_save = []
    for template in AccountTemplate.search([]):
        if template.type or template.childs:
            continue
        code = template.code[:-1]
        cursor.execute(
            "select id, code, type  from account_account_template where code like '%s' and type > 0 limit 1" % code)
        res = cursor.fetchone()
        if not res:
            code = code[:-1]
            cursor.execute(
                "select id, code, type  from account_account_template where code like '%s' and type > 0 limit 1" % code)
            res = cursor.fetchone()

        if res:
            id, code, type  = res
            template.type = type
        to_save.append(template)

    AccountTemplate.save(to_save)
    Transaction().commit()

    cursor.execute(''' update account_move_line set party=%s where id in (
        select l.id from account_move_line l, account_account a where
        l.account=a.id and a.party_required and l.party is null) ''' %
        party.id)

    UpdateChart = pool.get('account.update_chart', type='wizard')

    Account.parent.left = None
    Account.parent.right = None
    Account._mptt_fields = set()

    if domain is None:
        domain=[]

    for company in Company.search(domain):
        logger.info("company %s" % company.id)
        user.companies += (company,)
        user.company = company.id
        user.save()
        with Transaction().set_context(company=company.id):
            config = Configuration(1)

            if not config.default_account_code_digits:
                config.default_account_code_digits = digits
                config.force_digits = False
                config.save()

            print("digits:", digits, config.default_account_code_digits)

            template = AccountTemplate(ModelData.get_id('account_es', 'pgc_0'))
            account = Account.search([('template', '=', template),
                ('company','=', company.id)], limit=1)

            if not account:
                print("No Account Found for company:", company.id)
                continue

            account = account[0]

            session_id, _, _ = UpdateChart.create()
            update_chart = UpdateChart(session_id)
            update_chart.start.account = account
            update_chart.start.account_code_digits = config.default_account_code_digits
            #print(update_chart.start.account_code_digits)
            logger.info('%s: Upgrading Account Chart' % (company.rec_name))
            update_chart.transition_update()
            logger.info('%s: End Account Chart' % (company.rec_name))

            Transaction().commit()

    Account.parent.left = 'left'
    Account.parent.right = 'right'

    # for company in Company.search(domain):
    #      logger.info("company %s" % company.id)
    #      logger.info('%s: Rebuild tree' % (company.rec_name))
    #      with Transaction().set_context(company=company.id):
    #          Account._rebuild_tree('parent', None, 0)
    #      logger.info('%s: End rebuild tree' % (company.rec_name))
    #
    # logger.info('Done')


    # Fast way to calculate parent_left and right
    cr = Transaction().connection.cursor()

    def browse_rec(root, pos=0):
        where = 'parent' + '=' + str(root)

        if not root:
            where = 'parent IS NULL'

        cr.execute('SELECT id FROM %s WHERE %s \
            ORDER BY %s' % ('account_account', where, 'parent'))
        pos2 = pos + 1
        childs = cr.fetchall()
        for id in childs:
            pos2 = browse_rec(id[0], pos2)
        cr.execute('update %s set "left"=%s, "right"=%s\
            where id=%s' % ('account_account', pos, pos2, root))
        return pos2 + 1

    query = 'SELECT id FROM %s WHERE %s IS NULL order by %s' % (
        'account_account', 'parent', 'parent')
    pos = 0
    cr.execute(query)
    for (root,) in cr.fetchall():
        pos = browse_rec(root, pos)

    cr.execute(query)
    for (root,) in cr.fetchall():
        pos = browse_rec(root, pos)

    Transaction().commit()
