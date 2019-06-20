#!/usr/bin/env python
import sys
import os

dbname = sys.argv[1]
config_file = sys.argv[2]
digits = sys.argv[3] if len(sys.argv) == 4 else 7
domain = sys.argv[4] if len(sys.argv) == 5 else None
if domain:
    domain = eval(domain)

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)


from trytond.transaction import Transaction
from trytond.pool import Pool
import trytond.tools as tools
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
        party = Party(name='Generic for Party required Accounts')
        party.save()
    else:
        party, = party

    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id

    cursor = Transaction().connection.cursor()

    cursor.execute('''select t.id from account_account_template t
        where  t.id not in (select db_id from ir_model_data where
        module='account_es' and model='account.account.template')
        and t.code != '' order by t.code asc''' )

    template_ids = [x[0] for x in cursor.fetchall()]

    to_save = []
    for template in AccountTemplate.browse(template_ids):
        if not template.type:
            continue

        code = template.code[:-1].replace('%','0') +'0'
        code = code[0:4]
        similar = AccountTemplate.search([('code', '=', code),
            ('id', 'not in', template_ids)])

        if not similar:
            code = code[:-1]
            similar = AccountTemplate.search([('code', '=', code),
            ('id', 'not in', template_ids)])

        if not similar:
            code = code[:-2] + "00"
            similar = AccountTemplate.search([('code', '=', code),
                ('id', 'not in', template_ids)])
        if not similar:
            code = code[:-1]
            similar = AccountTemplate.search([('code', '=', code),
                ('id', 'not in', template_ids)])
        if not similar:
            code = code[:-3] + "000"
            similar = AccountTemplate.search([('code', '=', code),
                ('id', 'not in', template_ids)])
        if not similar:
            code = code[:-1]
            # print("code 2:", template.code, code)
            similar = AccountTemplate.search([('code', '=', code),
                ('id', 'not in', template_ids)])
        if not similar:
            print("not found last:", template.code, code)
            continue

        template.type = similar[0].type
        try:
            template.save()
        except:
            print("a revisar:", template.code)
        #to_save.append(template)

    #AccountTemplate.save(to_save)
    Transaction().commit()

    cursor.execute(''' update account_move_line set party=%s where id in (
        select l.id from account_move_line l, account_account a where
        l.account=a.id and a.party_required and l.party is null) ''' %
        party.id)

    UpdateChart = pool.get('account.update_chart', type='wizard')

    Account.parent.left = None
    Account.parent.right = None

    print("domain:", domain)
    if domain is None:
        print("Get childs")
        child_companies = Company.search([('parent', '!=', None)])
        if child_companies:
            domain=[('parent', '!=', None)]

    for company in Company.search(domain):
        logger.info("company %s" % company.id)
        user.main_company=company.id
        user.company = company.id
        user.save()
        with Transaction().set_context(company=company.id):

            template = AccountTemplate(ModelData.get_id('account_es', 'pgc_0'))
            account = Account.search([('template', '=', template),
                ('company','=', company.id)], limit=1)

            if not account:
                print("No Account Found for company:", company.id)
                continue

            account = account[0]

            config = Configuration(1)

            if not config.default_account_code_digits:
                config.default_account_code_digits = digits
                config.force_digits = False
                config.save()

            print("digits:", digits, config.default_account_code_digits)
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
            where = field + 'IS NULL'

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
