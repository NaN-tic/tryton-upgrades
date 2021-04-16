from trytond.transaction import Transaction

transaction.set_user(1)

Configuration = pool.get('account.configuration')
UpdateChart = pool.get('account.update_chart', type='wizard')
AccountTemplate = pool.get('account.account.template')
ModelData = pool.get('ir.model.data')
Account = pool.get('account.account')
Company = pool.get('company.company')
User = pool.get('res.user')

context = User.get_preferences(context_only=True)
transaction.set_context(context)

admin_user, = User.search([('login', '=', 'admin')], limit=1)

for company in Company.search([]):
    with Transaction().new_transaction() as new_transaction:
        print('Company: ', company.rec_name)
        admin_user.company = company
        admin_user.save()
        new_transaction.commit()

        context = User.get_preferences(context_only=True)
        new_transaction.set_context(context)

        template = AccountTemplate(ModelData.get_id('account_es', 'pgc_0'))
        account = Account.search([('template', '=', template)], limit=1)
        if not account:
            continue

        account = account[0]
        config = Configuration(1)
        account_code_digits = config.default_account_code_digits
        if not account_code_digits:
            continue

        session_id, _, _ = UpdateChart.create()
        update_chart = UpdateChart(session_id)
        update_chart.start.account = account
        update_chart.start.account_code_digits = account_code_digits
        update_chart.transition_update()
        new_transaction.commit()
