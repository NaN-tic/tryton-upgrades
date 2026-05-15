#!/usr/bin/env python
import sys
import logging

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction

Pool.start()
pool = Pool(dbname)
pool.init()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

context = {'active_test': False}
with Transaction().start(dbname, 0, context=context):
    pool = Pool()
    ModelData = pool.get('ir.model.data')
    Sequence = pool.get('ir.sequence')

    old_data = ModelData.search([
            ('fs_id', '=', 'sequence_work'),
            ('module', '=', 'project_sequence'),
            ], limit=1)
    new_data = ModelData.search([
            ('fs_id', '=', 'sequence_work'),
            ('module', '=', 'project'),
            ], limit=1)

    if not old_data or not new_data:
        logger.info(
            'No sequence migration done: old_data=%s new_data=%s',
            bool(old_data), bool(new_data))
        Transaction().commit()
        sys.exit(0)

    old_data, = old_data
    new_data, = new_data

    old_sequence = Sequence(old_data.db_id)
    new_sequence = Sequence(new_data.db_id)

    logger.info(
        'Copying values from project_sequence sequence %s to project sequence %s',
        old_sequence.id, new_sequence.id)

    new_sequence.number_next = old_sequence.number_next
    new_sequence.padding = old_sequence.padding
    new_sequence.number_increment = old_sequence.number_increment
    new_sequence.prefix = old_sequence.prefix
    new_sequence.suffix = old_sequence.suffix
    new_sequence.save()

    logger.info(
        'Copied values: number_next_internal=%s padding=%s '
        'number_increment=%s prefix=%r suffix=%r',
        new_sequence.number_next_internal,
        new_sequence.padding,
        new_sequence.number_increment,
        new_sequence.prefix,
        new_sequence.suffix)

    Transaction().commit()
