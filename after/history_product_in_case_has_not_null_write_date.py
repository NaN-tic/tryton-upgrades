# If the __history table has no records with a write_date set to NULL,
# an AccessError is raised because no records will be returned.
# When the _history (trytond-admin --all) is activated, it creates these records
# with a write_date set to NULL.

from trytond.modules.product.product import round_price
from decimal import Decimal
from datetime import datetime, date

User = pool.get('res.user')
Company = pool.get('company.company')
Party = pool.get('party.party')
Sale = pool.get('sale.sale')
Line = pool.get('sale.line')

transaction.set_user(1)
cursor = transaction.connection.cursor()

for table_name in ('product_template', 'product_product'):
    # print(table_name)
    query = "SELECT column_name FROM information_schema.columns WHERE table_name = '%(table_name)s__history'" % {'table_name': table_name}
    # print(query)
    cursor.execute(query)
    columns = [row[0] for row in cursor.fetchall()]

    # Excloem les columnes que no volem
    excluded_columns = {'__id', 'write_date'}
    selected_columns = [col for col in columns if col not in excluded_columns]
    columns_str = ", ".join(selected_columns)

    query = """
        select id from %(table_name)s where id not in
        (select t.id from %(table_name)s as t left join %(table_name)s__history as h on t.id = h.id where h.write_date is null)
        """ % {'table_name': table_name}
    # print(query)
    cursor.execute(query)
    for template_id, in cursor.fetchall():
        query = """
            select id, __id, create_date, write_date from %(table_name)s__history where id = %(id)s order by create_date ASC, write_date ASC limit 1
            """ % {'table_name': table_name, 'id': template_id}
        cursor.execute(query)
        last_history = cursor.fetchone()

        query = """
            INSERT INTO %(table_name)s__history (%(columns_str)s, write_date)
            SELECT %(columns_str)s, NULL AS write_date
            FROM %(table_name)s__history
            WHERE __id = %(id)s
            """ % {'table_name': table_name, 'columns_str': columns_str, 'id': last_history[1]}
        # print(query)
        cursor.execute(query)

transaction.commit()
print('------')
