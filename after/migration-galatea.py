#!/usr/bin/env python
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.tools.email_ import normalize_email

Pool.start()
pool = Pool(dbname)
pool.init()

context = {}

with Transaction().start(dbname, 0, context=context) as transaction:
    GalateaUser = pool.get('galatea.user')
    WebUser = pool.get('web.user')
    WebUser.check_valid_email = classmethod(
        lambda cls, users, fields_names=None: None)

    web_users = WebUser.search([])
    emails = {
        normalize_email(web_user.email).lower()
        for web_user in web_users if web_user.email
    }

    for galatea_user in GalateaUser.search([]):
        email = galatea_user.email
        if not email:
            continue

        normalized_email = normalize_email(email).lower()
        if normalized_email in emails:
            continue

        hash_sha1 = '$'.join([
            'sha1', galatea_user.password, galatea_user.salt,
        ])

        user = WebUser()
        user.email = email
        user.email_valid = True
        user.party = galatea_user.party
        user.password_hash = hash_sha1
        user.save()
        emails.add(normalized_email)

    transaction.commit()
