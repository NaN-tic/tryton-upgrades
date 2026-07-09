#!/usr/bin/env python
import logging
import sys

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
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


# Reports already provided by html_report must keep behaving as the
# html_report base report. During migration we reuse that canonical
# definition and, when needed, copy it onto the legacy ids that are still
# referenced by customer configuration or open documents.
MODEL_DATA_ALIASES = {
    'account.invoice': ('html_report', 'html_report_invoice'),
}

PRESERVED_TARGETS = {}


def get_report_by_model_data(ActionReport, ModelData, module, fs_id):
    if not module or not fs_id:
        return None
    data = ModelData.search([
            ('model', '=', 'ir.action.report'),
            ('module', '=', module),
            ('fs_id', '=', fs_id),
            ], limit=1)
    if data:
        return ActionReport(data[0].db_id)
    return None


def get_report_by_report_name(ActionReport, report_name, model):
    domain = [('report_name', '=', report_name)]
    if model:
        domain.append(('model', '=', model))

    reports = ActionReport.search(
        domain + [('template_extension', '=', 'html')],
        limit=1)
    if reports:
        return reports[0]

    reports = ActionReport.search(
        domain + [('template_extension', '!=', 'jinja')],
        limit=1)
    if reports:
        return reports[0]
    return None


def get_action_name(report_id):
    cursor = Transaction().connection.cursor()
    cursor.execute("""
        SELECT action.name
        FROM ir_action_report report
        JOIN ir_action action ON action.id = report.id
        WHERE report.id = %s
    """, (report_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def copy_report_definition(source_id, target_id, preserve_action_name=True):
    cursor = Transaction().connection.cursor()
    cursor.execute("""
        UPDATE ir_action
        SET active = source.active,
            icon = source.icon,
            records = source.records,
            type = source.type,
            usage = source.usage
        FROM ir_action AS source
        WHERE ir_action.id = %s
          AND source.id = %s
    """, (target_id, source_id))
    if not preserve_action_name:
        cursor.execute("""
            UPDATE ir_action
            SET name = source.name
            FROM ir_action AS source
            WHERE ir_action.id = %s
              AND source.id = %s
        """, (target_id, source_id))

    cursor.execute("""
        UPDATE ir_action_report
        SET direct_print = source.direct_print,
            extension = source.extension,
            model = source.model,
            module = source.module,
            report = source.report,
            report_content_custom = source.report_content_custom,
            report_name = source.report_name,
            single = source.single,
            template_extension = source.template_extension,
            translatable = source.translatable,
            file_name = source.file_name,
            html_footer_template = source.html_footer_template,
            html_header_template = source.html_header_template,
            html_last_footer_template = source.html_last_footer_template,
            html_raise_user_error = source.html_raise_user_error,
            html_template = source.html_template,
            jinja_template = source.jinja_template,
            html_copies = source.html_copies,
            html_zipped = source.html_zipped,
            record_name = source.record_name,
            html_extra_vertical_margin = source.html_extra_vertical_margin,
            html_side_margin = source.html_side_margin,
            html_file_name = source.html_file_name
        FROM ir_action_report AS source
        WHERE ir_action_report.id = %s
          AND source.id = %s
    """, (target_id, source_id))


def move_model_data(source_id, target_id):
    cursor = Transaction().connection.cursor()
    cursor.execute("""
        UPDATE ir_model_data
        SET db_id = %s
        WHERE model = 'ir.action.report'
          AND db_id = %s
    """, (target_id, source_id))


def get_legacy_reports_for_target(target_report):
    cursor = Transaction().connection.cursor()
    cursor.execute("""
        SELECT report.id, action.name
        FROM ir_action_report report
        JOIN ir_action action ON action.id = report.id
        LEFT JOIN ir_model_data imd
            ON imd.model = 'ir.action.report'
           AND imd.db_id = report.id
        WHERE report.template_extension = 'jinja'
          AND report.model = %s
          AND report.report_name = %s
          AND imd.id IS NULL
        ORDER BY report.id
    """, (target_report.model, target_report.report_name))
    return cursor.fetchall()


def preserve_target_report_id(target_report):
    preserved_id = PRESERVED_TARGETS.get(target_report.id)
    if preserved_id is not None:
        return preserved_id

    target_action_name = get_action_name(target_report.id)
    legacy_reports = get_legacy_reports_for_target(target_report)
    if not legacy_reports:
        PRESERVED_TARGETS[target_report.id] = target_report.id
        return target_report.id

    primary_id = None
    for legacy_id, legacy_action_name in legacy_reports:
        if legacy_action_name == target_action_name:
            primary_id = legacy_id
            break
    if primary_id is None:
        primary_id = min(report_id for report_id, _name in legacy_reports)

    # Keep legacy ids valid for customer-specific links while moving the
    # canonical ir.model.data entry to one preserved legacy id.
    for legacy_id, _legacy_action_name in legacy_reports:
        copy_report_definition(target_report.id, legacy_id)
    move_model_data(target_report.id, primary_id)

    PRESERVED_TARGETS[target_report.id] = primary_id
    logger.info(
        'Preserved report %s on legacy id %s',
        target_report.report_name, primary_id)
    return primary_id


def preserve_specific_legacy_report(old_report_id, target_report):
    if old_report_id == target_report.id:
        return target_report.id
    copy_report_definition(target_report.id, old_report_id)
    return old_report_id


def get_report_from_backup(pool, backup_row):
    ActionReport = pool.get('ir.action.report')
    ModelData = pool.get('ir.model.data')

    (_configuration_id, _company, old_report_id, report_name, model,
        _template_extension, _html_template, _jinja_template, module,
        fs_id) = backup_row

    report = get_report_by_model_data(ActionReport, ModelData, module, fs_id)
    if report:
        preserve_target_report_id(report)
        if old_report_id != report.id:
            preserve_specific_legacy_report(old_report_id, report)
            return ActionReport(old_report_id)
        return report

    alias = MODEL_DATA_ALIASES.get(report_name)
    if alias:
        report = get_report_by_model_data(ActionReport, ModelData, *alias)
        if report:
            preserve_target_report_id(report)
            preserve_specific_legacy_report(old_report_id, report)
            return ActionReport(old_report_id)

    report = get_report_by_report_name(ActionReport, report_name, model)
    if report:
        preserve_target_report_id(report)
        if old_report_id != report.id:
            preserve_specific_legacy_report(old_report_id, report)
            return ActionReport(old_report_id)
        return report

    logger.warning(
        'No invoice report mapping found for backup report %s (%s)',
        old_report_id, report_name)
    return None


def get_company_default_report(config):
    if config and config.invoice_action_report:
        return config.invoice_action_report
    return None


def get_invoice_report(invoice, default_report):
    if not invoice.party:
        return default_report

    alternative_reports = [
        alternative.report for alternative in invoice.party.alternative_reports
        if alternative.model_name == 'account.invoice' and alternative.report]

    if len(alternative_reports) == 1:
        return alternative_reports[0]
    if len(alternative_reports) > 1:
        return None
    return default_report


with Transaction().start(dbname, 0, context={'active_test': False}):
    pool = Pool()
    AccountConfigurationCompany = pool.get('account.configuration.company')
    AccountConfiguration = pool.get('account.configuration')
    Invoice = pool.get('account.invoice')

    cursor = Transaction().connection.cursor()
    cursor.execute("SELECT to_regclass('upgrade_backup_invoice_action_report')")
    backup_table, = cursor.fetchone()

    updated_companies = 0
    if backup_table:
        cursor.execute("""
            SELECT configuration_id, company, old_report_id, report_name, model,
                template_extension, html_template, jinja_template, module, fs_id
            FROM upgrade_backup_invoice_action_report
            ORDER BY configuration_id
        """)

        for backup_row in cursor.fetchall():
            configuration_id = backup_row[0]
            configuration = AccountConfigurationCompany(configuration_id)
            if configuration.invoice_action_report:
                continue

            report = get_report_from_backup(pool, backup_row)
            if not report:
                continue

            configuration.invoice_action_report = report
            configuration.save()
            updated_companies += 1

    draft_invoices = Invoice.search([
            ('invoice_action_report', '=', None),
            ('state', 'not in', ['posted', 'paid', 'cancelled']),
            ])

    updated_invoices = 0
    for invoice in draft_invoices:
        with Transaction().set_context(company=invoice.company.id):
            default_report = get_company_default_report(AccountConfiguration(1))
        report = get_invoice_report(invoice, default_report)
        if not report:
            continue
        invoice.invoice_action_report = report
        invoice.save()
        updated_invoices += 1

    if backup_table:
        cursor.execute('DROP TABLE IF EXISTS upgrade_backup_invoice_action_report')
    Transaction().commit()

    logger.info(
        'Updated %s company defaults and %s open invoices',
        updated_companies, updated_invoices)
