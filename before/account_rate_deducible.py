#!/usr/bin/env python
import logging
import sys
from decimal import Decimal

from trytond.config import config as CONFIG

dbname = sys.argv[1]
config_file = sys.argv[2]
CONFIG.update_etc(config_file)

from trytond.pool import Pool
from trytond.tools import grouped_slice
from trytond.transaction import Transaction


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
LOGGER.addHandler(handler)

OLD_NEW_FS_IDS = {
    'iva_no_ded_4': 'iva_sop_4',
    'iva_no_ded_10': 'iva_sop_10',
    'iva_no_ded_21': 'iva_sop_21',
}
DELETE_FS_IDS = [
    'vat_code_chart_no_ded',
    'iva_no_ded_4',
    'iva_no_ded_10',
    'iva_no_ded_21',
    'iva_no_ded_22',
    'iva_no_ded_22_4',
    'iva_no_ded_22_10',
    'iva_no_ded_22_21',
    'iva_no_ded_cuota_23',
    'iva_no_ded_cuota_23_4',
    'iva_no_ded_cuota_23_10',
    'iva_no_ded_cuota_23_21',
    'iva_no_ded_4-iva_no_ded_22_4-invoice-base',
    'iva_no_ded_4-iva_no_ded_cuota_23_4-invoice-tax',
    'iva_no_ded_4-iva_no_ded_22_4-credit-base',
    'iva_no_ded_4-iva_no_ded_cuota_23_4-credit-tax',
    'iva_no_ded_10-iva_no_ded_22_10-invoice-base',
    'iva_no_ded_10-iva_no_ded_cuota_23_10-invoice-tax',
    'iva_no_ded_10-iva_no_ded_22_10-credit-base',
    'iva_no_ded_10-iva_no_ded_cuota_23_10-credit-tax',
    'iva_no_ded_21-iva_no_ded_22_21-invoice-base',
    'iva_no_ded_21-iva_no_ded_cuota_23_21-invoice-tax',
    'iva_no_ded_21-iva_no_ded_22_21-credit-base',
    'iva_no_ded_21-iva_no_ded_cuota_23_21-credit-tax',
]
DELETE_MODEL_DATA = {
    'account_es': DELETE_FS_IDS,
    'aeat_347': [
        'account_es.iva_no_ded_4',
        'account_es.iva_no_ded_10',
        'account_es.iva_no_ded_21',
        ],
    'aeat_sii': [
        'account_es.iva_no_ded_4',
        'account_es.iva_no_ded_10',
        'account_es.iva_no_ded_21',
        ],
    'aeat_303': [
        'aeat_303_prorrata_mapping_iva_no_ded_22',
        ],
    }
END_DATE = '2025-12-31'


def get_tax_templates(ModelData):
    templates = {}
    for fs_id in set(OLD_NEW_FS_IDS) | set(OLD_NEW_FS_IDS.values()):
        records = ModelData.search([
                ('module', '=', 'account_es'),
                ('model', '=', 'account.tax.template'),
                ('fs_id', '=', fs_id),
                ], limit=1)
        if records:
            templates[fs_id] = records[0].db_id
    return templates


def get_company_taxes(Tax, company_id, template_ids):
    taxes = {}
    if not template_ids:
        return taxes
    found = Tax.search([
            ('company', '=', company_id),
            ('template', 'in', list(template_ids.values())),
            ])
    for tax in found:
        taxes[tax.template.id] = tax
    return taxes


def replace_supplier_taxes(records, old_to_new):
    return replace_taxes(records, old_to_new, 'supplier_taxes',
        'supplier_taxes_deductible_rate')


def replace_invoice_line_taxes(records, old_to_new):
    return replace_taxes(records, old_to_new, 'taxes',
        'taxes_deductible_rate')


def replace_taxes(records, old_to_new, taxes_field, deductible_rate_field):
    to_save = []
    for record in records:
        current = list(getattr(record, taxes_field) or [])
        replaced = False
        new_taxes = []
        seen = set()
        for tax in current:
            mapped = old_to_new.get(tax.id, tax)
            if mapped.id != tax.id:
                replaced = True
            if mapped.id in seen:
                continue
            seen.add(mapped.id)
            new_taxes.append(mapped)
        if not replaced:
            continue
        setattr(record, taxes_field, new_taxes)
        setattr(record, deductible_rate_field, Decimal('0'))
        to_save.append(record)
    return to_save


def deactivate_old_templates(TaxTemplate, tax_templates):
    old_template_ids = [
        tax_templates[fs_id] for fs_id in OLD_NEW_FS_IDS
        if fs_id in tax_templates
    ]
    if not old_template_ids:
        return 0
    templates = TaxTemplate.browse(old_template_ids)
    to_save = []
    for template in templates:
        if str(template.end_date) == END_DATE and template.active is False:
            continue
        template.end_date = END_DATE
        template.active = False
        to_save.append(template)
    if to_save:
        TaxTemplate.save(to_save)
    return len(to_save)


def deactivate_old_taxes(old_taxes):
    to_save = []
    for old_tax in old_taxes:
        if str(old_tax.end_date) == END_DATE and old_tax.active is False:
            continue
        old_tax.end_date = END_DATE
        old_tax.active = False
        to_save.append(old_tax)
    return to_save


def delete_model_data(cursor):
    for module, fs_ids in DELETE_MODEL_DATA.items():
        placeholders = ', '.join(['%s'] * len(fs_ids))
        cursor.execute(
            ('DELETE FROM ir_model_data '
             'WHERE module = %s AND fs_id IN (%s)') % ('%s', placeholders),
            [module, *fs_ids])


Pool.start()
pool = Pool(dbname)
pool.init()

with Transaction().start(dbname, 0, context={}) as transaction:
    Company = pool.get('company.company')
    ModelData = pool.get('ir.model.data')
    Category = pool.get('product.category')
    Tax = pool.get('account.tax')
    TaxTemplate = pool.get('account.tax.template')
    Template = pool.get('product.template')
    Invoice = pool.get('account.invoice')
    InvoiceLine = pool.get('account.invoice.line')

    tax_templates = get_tax_templates(ModelData)
    if len(tax_templates) < len(OLD_NEW_FS_IDS) + len(OLD_NEW_FS_IDS.values()):
        LOGGER.info('Missing account_es tax templates. Skipping migration.')
        delete_model_data(transaction.connection.cursor())
        transaction.commit()
        raise SystemExit(0)

    template_has_supplier_taxes = (
        'supplier_taxes' in Template._fields
        and 'supplier_taxes_deductible_rate' in Template._fields)
    deactivated = deactivate_old_templates(TaxTemplate, tax_templates)
    LOGGER.info('Deactivated %s old tax templates.', deactivated)

    for company in Company.search([]):
        with Transaction().set_context(company=company.id, active_test=False):
            company_taxes = get_company_taxes(Tax, company.id, tax_templates)
            if not company_taxes:
                LOGGER.info('%s: account_es taxes not found, skipping company.',
                    company.rec_name)
                continue

            old_tax_map = {}
            old_taxes = []
            for old_fs_id, new_fs_id in OLD_NEW_FS_IDS.items():
                old_template_id = tax_templates[old_fs_id]
                new_template_id = tax_templates[new_fs_id]
                old_tax = company_taxes.get(old_template_id)
                new_tax = company_taxes.get(new_template_id)
                if old_tax and new_tax:
                    old_tax_map[old_tax.id] = new_tax
                    old_taxes.append(old_tax)

            if not old_tax_map:
                LOGGER.info('%s: no non-deductible taxes to migrate.',
                    company.rec_name)
                continue

            categories = Category.search([
                    ('accounting', '=', True),
                    ('supplier_taxes', 'in', list(old_tax_map.keys())),
                    ])
            to_save_categories = replace_supplier_taxes(
                categories, old_tax_map)
            for sub_records in grouped_slice(to_save_categories):
                Category.save(list(sub_records))
            LOGGER.info('%s: updated %s categories.',
                company.rec_name, len(to_save_categories))

            if template_has_supplier_taxes:
                templates = Template.search([
                        ('supplier_taxes', 'in', list(old_tax_map.keys())),
                        ])
                to_save_templates = replace_supplier_taxes(
                    templates, old_tax_map)
                for sub_records in grouped_slice(to_save_templates):
                    Template.save(list(sub_records))
                LOGGER.info('%s: updated %s templates.',
                    company.rec_name, len(to_save_templates))

            invoice_lines = InvoiceLine.search([
                    ('invoice.company', '=', company.id),
                    ('invoice.state', '=', 'draft'),
                    ('taxes', 'in', list(old_tax_map.keys())),
                    ])
            to_save_lines = replace_invoice_line_taxes(
                invoice_lines, old_tax_map)
            for sub_records in grouped_slice(to_save_lines):
                InvoiceLine.save(list(sub_records))
            invoice_ids = list({
                    line.invoice.id for line in to_save_lines if line.invoice
                    })
            if invoice_ids:
                Invoice.update_taxes(Invoice.browse(invoice_ids))
            LOGGER.info('%s: updated %s draft invoice lines.',
                company.rec_name, len(to_save_lines))

            to_save_taxes = deactivate_old_taxes(old_taxes)
            if to_save_taxes:
                Tax.save(to_save_taxes)
            LOGGER.info('%s: deactivated %s taxes.',
                company.rec_name, len(to_save_taxes))

        transaction.commit()

    delete_model_data(transaction.connection.cursor())
    transaction.commit()
    LOGGER.info('Done')
