pool = globals().get('pool')
transaction = globals().get('transaction')

MoveLine = pool.get('account.move.line')

MoveLine.set_payment_amount()

transaction.commit()
