#!/usr/bin/env python
import logging
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond.config import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


QUERY = """
    SELECT c.table_name
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema
     AND t.table_name = c.table_name
    WHERE c.table_schema = 'public'
      AND t.table_type = 'BASE TABLE'
      AND c.column_name = 'id'
      AND NOT EXISTS (
          SELECT 1
          FROM pg_constraint con
          JOIN pg_class rel ON rel.oid = con.conrelid
          JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
          JOIN pg_attribute attr
            ON attr.attrelid = rel.oid
           AND attr.attnum = ANY (con.conkey)
          WHERE nsp.nspname = 'public'
            AND rel.relname = c.table_name
            AND con.contype IN ('p', 'u')
            AND attr.attname = 'id')
    ORDER BY c.table_name
"""


with Transaction().start(dbname, 0, context={}):
    cursor = Transaction().connection.cursor()
    cursor.execute(QUERY)
    tables = [row[0] for row in cursor.fetchall()]

    processed = 0
    skipped = 0
    for table_name in tables:
        cursor.execute(
            f'SELECT id, COUNT(*) '
            f'FROM "{table_name}" '
            f'GROUP BY id HAVING COUNT(*) > 1 '
            f'ORDER BY COUNT(*) DESC, id '
            f'LIMIT 5')
        duplicates = cursor.fetchall()
        if duplicates:
            skipped += 1
            logger.warning(
                'Skip %s because id is duplicated. Examples: %s',
                table_name, duplicates)
            continue

        cursor.execute("""
            SELECT 1
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = 'public'
              AND rel.relname = %s
              AND con.contype = 'p'
            LIMIT 1
        """, (table_name,))
        has_primary_key = bool(cursor.fetchone())

        if has_primary_key:
            constraint_name = f'{table_name}_id_uniq'
            sql = (
                f'ALTER TABLE "{table_name}" '
                f'ADD CONSTRAINT "{constraint_name}" UNIQUE (id)'
            )
        else:
            constraint_name = f'{table_name}_pkey'
            sql = (
                f'ALTER TABLE "{table_name}" '
                f'ADD CONSTRAINT "{constraint_name}" PRIMARY KEY (id)'
            )
        cursor.execute(sql)
        processed += 1
        logger.info(
            'Added %s on %s(id)',
            'UNIQUE' if has_primary_key else 'PRIMARY KEY', table_name)

    Transaction().commit()
    logger.info('Processed %s tables, skipped %s tables', processed, skipped)
