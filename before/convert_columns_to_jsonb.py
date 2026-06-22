#!/usr/bin/env python
import json
import logging
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.transaction import Transaction


COLUMNS_TO_CONVERT = [
    ('ir_attachment', 'copy_to_resources'),
    ('ir_note', 'copy_to_resources'),
    ('ir_avatar', 'copy_to_resources'),
    ('party_address_subdivision_type', 'types'),
    ('party_configuration', 'identifier_types'),
    ('party_relation_type', 'usages'),
    ('project_work_status', 'types'),
    ('activity_activity', 'translation_languages'),
    ('account_statement_origin', 'information'),
    ('product_template', 'custom_attributes'),
]


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def get_column_info(cursor, table_name, column_name):
    cursor.execute("""
        SELECT data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        """, (table_name, column_name))
    return cursor.fetchone()


def find_invalid_rows(cursor, table_name, column_name):
    query = (
        f'SELECT id, "{column_name}" '
        f'FROM "{table_name}" '
        f'WHERE "{column_name}" IS NOT NULL'
    )
    cursor.execute(query)

    invalid_ids = []
    invalid_count = 0
    for record_id, value in cursor.fetchall():
        if not isinstance(value, str):
            continue
        trimmed = value.strip()
        if not trimmed:
            continue
        try:
            json.loads(trimmed)
        except (TypeError, ValueError):
            invalid_count += 1
            if len(invalid_ids) < 20:
                invalid_ids.append(record_id)
    return invalid_count, invalid_ids


def convert_column_to_jsonb(cursor, table_name, column_name):
    info = get_column_info(cursor, table_name, column_name)
    if not info:
        logger.info(
            'Skip %s.%s because the column does not exist',
            table_name, column_name)
        return

    data_type, udt_name = info
    if udt_name == 'jsonb':
        logger.info(
            'Skip %s.%s because it is already jsonb',
            table_name, column_name)
        return

    if udt_name == 'json':
        alter_query = (
            f'ALTER TABLE "{table_name}" '
            f'ALTER COLUMN "{column_name}" TYPE jsonb '
            f'USING "{column_name}"::jsonb'
        )
        cursor.execute(alter_query)
        logger.info('Converted %s.%s from json to jsonb', table_name, column_name)
        return

    if data_type not in {'character varying', 'text'}:
        logger.warning(
            'Skip %s.%s because its type is %s (%s), not varchar/text',
            table_name, column_name, data_type, udt_name)
        return

    update_query = (
        f'UPDATE "{table_name}" '
        f'SET "{column_name}" = NULL '
        f'WHERE "{column_name}" IS NOT NULL '
        f"  AND btrim(\"{column_name}\") = ''"
    )
    cursor.execute(update_query)

    invalid_count, invalid_ids = find_invalid_rows(cursor, table_name, column_name)
    if invalid_count:
        logger.warning(
            'Skip %s.%s because %s rows do not contain valid JSON. '
            'Example ids: %s',
            table_name, column_name, invalid_count, invalid_ids)
        return

    alter_query = (
        f'ALTER TABLE "{table_name}" '
        f'ALTER COLUMN "{column_name}" TYPE jsonb '
        f'USING "{column_name}"::jsonb'
    )
    cursor.execute(alter_query)
    logger.info('Converted %s.%s to jsonb', table_name, column_name)


Pool.start()
pool = Pool(dbname)
pool.init()

with Transaction().start(dbname, 1, context={}):
    cursor = Transaction().connection.cursor()
    for table_name, column_name in COLUMNS_TO_CONVERT:
        convert_column_to_jsonb(cursor, table_name, column_name)

    Transaction().commit()
    logger.info('Done')
