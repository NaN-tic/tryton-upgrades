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


MODEL_DATA_ALIASES = {
    'stock.shipment.out.valued_delivery_note.copy': (
        'html_report', 'html_report_valued_delivery_note'),
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


def get_report_by_report_name(ActionReport, report_name, model, single):
    domain = [('report_name', '=', report_name)]
    if model:
        domain.append(('model', '=', model))

    reports = ActionReport.search(
        domain + [('template_extension', '=', 'html'),
            ('single', '=', bool(single))],
        limit=1)
    if reports:
        return reports[0]

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

    (_modality_id, old_report_id, report_name, model, _template_extension,
        single, module, fs_id) = backup_row

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

    report = get_report_by_report_name(
        ActionReport, report_name, model, single)
    if report:
        preserve_target_report_id(report)
        if old_report_id != report.id:
            preserve_specific_legacy_report(old_report_id, report)
            return ActionReport(old_report_id)
        return report

    logger.warning(
        'No modality report mapping found for modality %s from report %s (%s)',
        backup_row[0], old_report_id, report_name)
    return None


with Transaction().start(dbname, 0, context={'active_test': False}):
    pool = Pool()
    Relation = pool.get('party.modality-ir.action.report')

    cursor = Transaction().connection.cursor()
    cursor.execute("SELECT to_regclass('upgrade_backup_modality_reports')")
    backup_table, = cursor.fetchone()
    if not backup_table:
        logger.info('No modality report backup table found')
        raise SystemExit(0)

    cursor.execute("""
        SELECT modality_id, old_report_id, report_name, model,
            template_extension, single, module, fs_id
        FROM upgrade_backup_modality_reports
        ORDER BY modality_id, old_report_id
    """)
    backup_rows = cursor.fetchall()

    existing_relations = {
        (relation.modality.id, relation.report.id)
        for relation in Relation.search([])
    }

    created = 0
    skipped = 0
    for backup_row in backup_rows:
        modality_id = backup_row[0]
        report = get_report_from_backup(pool, backup_row)
        if not report:
            skipped += 1
            continue

        key = (modality_id, report.id)
        if key in existing_relations:
            continue

        Relation.create([{
                    'modality': modality_id,
                    'report': report.id,
                    }])
        existing_relations.add(key)
        created += 1

    cursor.execute('DROP TABLE IF EXISTS upgrade_backup_modality_reports')
    Transaction().commit()

    logger.info(
        'Created %s modality report relations, skipped %s without mapping',
        created, skipped)
