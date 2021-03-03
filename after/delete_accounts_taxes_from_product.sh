# ========= account =========
# backup product_template_account table
psql $1 -c "CREATE TABLE if not exists product_template_account_backup as (select * from product_template_account_backup);"

# eliminar tots els product_template_account quan el template ja té un account_category
psql $1 -c "delete from product_template_account where template in (select id from product_template where account_category is not null and accounts_category = True);"

# actualitzar el company segons el company del account
psql $1 -c "update product_template_account set company = sub.aacompany from (select pta.company, aa.company as aacompany, aa.id as aaid, pta.id as ptaid, pta.account_revenue, pta.template from product_template_account as pta left join account_account as aa on aa.id = pta.account_revenue where pta.company is null) as sub where id = sub.ptaid;"

# mirem si hi han template duplicats i mateix company a la taula product_template_account
# select template,count(*) from product_template_account group by (template, company) having count(*) > 1;

psql $1 -c "update product_template_account set account_revenue = sub.pta_account_revenue from (select pta.id as ptaid, pta.template as ptatemplate, pta.account_revenue as pta_account_revenue, pta.account_expense as pta_account_expense from product_template_account as pta where template in (select template from product_template_account group by (template, company) having count(*) > 1)) as sub where template = sub.ptatemplate and account_revenue is null;"

# eliminem duplicats account_expense
psql $1 -c "delete from product_template_account where account_expense is null and template in (select template from product_template_account where account_expense is not null);"

# check que no queden registres
# select * from product_template_account where account_revenue is null and template in (select template from product_template_account where account_revenue is not null);

# checks: només tenen account_revenue
# select * from product_template_account where account_expense is null;
# checks: només tenen account_expense
# select * from product_template_account where account_revenue is null;

# productes que tenen accounts_category però el account_category es null -> cal que ho revisin.
# select count(*) from product_template where account_category is null and accounts_category = True;

# check que tots els productes salable/purchasable tinguin compte (es pot fer de tots).

# ========= taxes =========

psql $1 -c "CREATE TABLE if not exists product_customer_taxes_rel_backup as (select * from product_customer_taxes_rel);"
psql $1 -c "CREATE TABLE if not exists product_supplier_taxes_rel_backup as (select * from product_supplier_taxes_rel);"

# eliminar tots els product_customer_taxes_rel quan el template ja té un taxes_category
psql $1 -c "delete from product_customer_taxes_rel where id in (select pctr.id as pctr_id from product_customer_taxes_rel as pctr left join product_template as pt on pt.id = pctr.product where pctr.product in (select id from product_template where taxes_category = True));"

# eliminar tots els product_supplier_taxes_rel quan el template ja té un taxes_category"
psql $1 -c "delete from product_supplier_taxes_rel where id in (select pctr.id as pctr_id from product_supplier_taxes_rel as pctr left join product_template as pt on pt.id = pctr.product where pctr.product in (select id from product_template where taxes_category = True));"
