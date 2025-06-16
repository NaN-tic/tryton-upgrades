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


with Transaction().start(dbname, 1, context=context):
    Account = pool.get('analytic_account.account')

    cursor = Transaction().connection.cursor()

    Account._mptt_fields = set()
    Account.parent.left = 'left'
    Account.parent.right = 'right'

    # Fast way to calculate parent_left and right
    cr = Transaction().connection.cursor()

    def browse_rec(root, pos=0):
        where = 'parent' + '=' + str(root)

        if not root:
            where = 'parent IS NULL'

        cr.execute('SELECT id FROM %s WHERE %s \
            ORDER BY %s' % ('analytic_account_account', where, 'parent'))
        pos2 = pos + 1
        childs = cr.fetchall()
        for id in childs:
            pos2 = browse_rec(id[0], pos2)
        cr.execute('update %s set "left"=%s, "right"=%s\
            where id=%s' % ('analytic_account_account', pos, pos2, root))
        return pos2 + 1

    query = 'SELECT id FROM %s WHERE %s IS NULL order by %s' % (
        'analytic_account_account', 'parent', 'parent')
    pos = 0
    cr.execute(query)
    for (root,) in cr.fetchall():
        pos = browse_rec(root, pos)

    cr.execute(query)
    for (root,) in cr.fetchall():
        pos = browse_rec(root, pos)

    Transaction().commit()
