User = pool.get('res.user')
context = User.get_preferences(context_only=True)

transaction.set_user(1)
transaction.set_context(context)
Template = pool.get('product.template')

# account_revenues
missing_account_revenues = []
for template in Template.search([('salable', '=', True)]):
    try:
        variable = template.account_revenue_used
    except:
        missing_account_revenues.append(template)
len(missing_account_revenues)

# account_expense
missing_account_expense = []
for template in Template.search([('purchasable', '=', True)]):
    try:
        template.account_expense_used
    except:
        variable = missing_account_expense.append(template)
len(missing_account_expense)

# customer_taxes
missing_customer_taxes = []
for template in Template.search([('salable', '=', True)]):
    if not template.get_taxes('customer_taxes'):
        missing_customer_taxes.append(template)
len(missing_customer_taxes)

# supplier_taxes
missing_supplier_taxes = []
for template in Template.search([('purchasable', '=', True)]):
    if not template.get_taxes('supplier_taxes'):
        missing_supplier_taxes.append(template)
len(missing_supplier_taxes)
