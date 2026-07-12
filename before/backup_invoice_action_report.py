#!/usr/bin/env python
import logging
import sys

dbname = sys.argv[1]
config_file = sys.argv[2]

from trytond import config as CONFIG
CONFIG.update_etc(config_file)

from trytond.transaction import Transaction

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


with Transaction().start(dbname, 0, context={'active_test': False}):
    cursor = Transaction().connection.cursor()
    cursor.execute("""
        SELECT 1
        FROM ir_module
        WHERE name = 'valero'
          AND state IN ('activated', 'to activate', 'to upgrade')
    """)
    if not cursor.fetchone():
        logger.info('Module valero is not active on %s, skipping', dbname)
        raise SystemExit(0)

    cursor.execute('DROP TABLE IF EXISTS upgrade_backup_invoice_action_report')
    cursor.execute("""
        CREATE TABLE upgrade_backup_invoice_action_report AS
        SELECT
            configuration.id AS configuration_id,
            configuration.company AS company,
            report.id AS old_report_id,
            report.report_name AS report_name,
            report.model AS model,
            report.template_extension AS template_extension,
            report.html_template AS html_template,
            report.jinja_template AS jinja_template,
            report.module AS module,
            model_data.fs_id AS fs_id
        FROM account_configuration_company configuration
        LEFT JOIN ir_action_report report
            ON report.id = configuration.invoice_action_report
        LEFT JOIN ir_model_data model_data
            ON model_data.model = 'ir.action.report'
           AND model_data.db_id = report.id
        WHERE configuration.invoice_action_report IS NOT NULL
    """)
    cursor.execute("""
        SELECT COUNT(*)
        FROM upgrade_backup_invoice_action_report
    """)
    count, = cursor.fetchone()
    Transaction().commit()
    logger.info('Backed up %s company invoice report defaults', count)
