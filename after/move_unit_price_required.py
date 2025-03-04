Move = pool.get('stock.move')

moves = Move.search([])
ids = []
for move in moves:
    if not move.unit_price_required:
        ids.append(str(move.id))

query = 'update stock_move set unit_price = null, currency=null where id in (%s)' % ','.join(ids)
print(query)

cursor = transaction.connection.cursor()
cursor.execute(query)
transaction.commit()
