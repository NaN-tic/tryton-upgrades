pool = globals().get('pool', None)
transaction = globals().get('transaction', None)

Template = pool.get('account.account.template')
Account = pool.get('account.account')
Company = pool.get('company.company')

templates = Template.search([])
for company in Company.search([]):
    transaction.set_context(company=1)

    for template in templates:
        code = template._get_account_value()['code']
        if Account.search([
                ('template', '!=', template),
                ('code', '=', code),
                ('company', '=', company)
                ]):
            print(template, code)

    # code templates found in account
    templates = [a.template for a in Account.search([('company', '=', company)])]
    for template in Template.search([('id', 'not in', templates)]):
        code = template._get_account_value()['code']
        if Account.search([
                ('code', '=', code),
                ('company', '=', company),
                ]):
            print("update account_account set template = %s where code ='%s' and template is null and company = %s;" % (template.id, code, company.id))
