#!/usr/bin/env python
import sys
import datetime
#from itertools import izip

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

with Transaction().start(dbname, 0, context=context):
    user_obj = pool.get('res.user')
    user = user_obj.search([('login', '=', 'admin')], limit=1)[0]
    user_id = user.id

with Transaction().start(dbname, 0, context=context) as transaction:

    Invoice = pool.get('account.invoice')
    SIILines = pool.get('aeat.sii.report.lines')

    limit = 5000
    offset = 0
    date = datetime.date(2018, 1, 1)

    cursor = Transaction().connection.cursor()

    import time
    start = time.time()
    while True:
        partial = time.time()
        lines = SIILines.search([
            ['OR',
                ('invoice.accounting_date', '>=', date),
                ('invoice.invoice_date', '>=', date),
                ],
            ('state', '!=', None),
            ('invoice.sii_header', '=', None),
            ], limit=limit, offset=offset)
        if not lines:
            break
        print('Search: ', len(lines), time.time() - partial)
        invoices = list(set([x.invoice.id for x in lines]))
        invoices = Invoice.browse(invoices)
        offset += limit

        res = Invoice.get_sii_state(invoices, ['sii_state',
            'sii_communication_type'])
        print ('Get1: ', time.time() - partial)
        partial_write = time.time()
        to_write = []
        for invoice in invoices:
            invoice.sii_state = res['sii_state'][invoice.id]
            invoice.sii_communication_type = res['sii_communication_type'][invoice.id]
            if invoice.state in ['posted', 'paid']:
                invoice.sii_pending_sending = True
                invoice.sii_header = str(Invoice.get_sii_header(invoice, False))
            if invoice.sii_state in ['Correcto', 'Correcta']:
                invoice.sii_pending_sending = False
            to_write.extend(([invoice], invoice._save_values))

        print ('Get2: ', time.time() - partial)

        if to_write:
            actions = iter(to_write)
            for invoices, values in zip(actions, actions):
                cursor.execute('UPDATE account_invoice SET sii_state=%s, '
                    'sii_communication_type=%s, sii_pending_sending=%s, '
                    'sii_header=%s WHERE id=%s', (values.get('sii_state'),
                    values.get('sii_communication_type'),
                    values.get('sii_pending_sending'),
                    values.get('sii_header'), invoices[0].id))
            Transaction().commit()
            end = time.time()
            print ('---', offset, end - start, end - partial,)
