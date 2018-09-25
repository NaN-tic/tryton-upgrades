UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'base_pymes_', 'base_') where fs_id like 'base_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'baser_pymes_', 'baser_') where fs_id like 'baser_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'cuota_pymes_', 'cuota_') where fs_id like 'cuota_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'cuotar_pymes_', 'cuotar_') where fs_id like 'cuotar_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'cuotas_pymes_', 'cuotas_') where fs_id like 'cuotas_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'es_balance_pymes', 'es_balance_normal') where fs_id like 'es_balance_pymes%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'es_pyg_pymes', 'es_pyg_normal') where fs_id like 'es_pyg_pymes%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'es_pymes', 'es') where fs_id = 'es_pymes' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'fp_pymes_', 'fp_') where fs_id like 'fp_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'fptt_pymes_', 'fptt_') where fs_id like 'fptt_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'igic_pymes_', 'igic_') where fs_id like 'igic_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'irpf_pymes_', 'irpf_') where fs_id like '%irpf_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'ispc_pymes', 'ispc') where fs_id = 'ispc_pymes' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'irpf_pymes_', 'irpf_') where fs_id like 'irpf_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'iva_pymes_', 'iva_') where fs_id like '%iva_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 're_pymes_', 're_') where fs_id like '%re_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'pgc_pymes_', 'pgc_') where fs_id like 'pgc_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'recc_pymes', 'recc') where fs_id like 'recc_pymes%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'suplido_pymes_', 'suplido_') where fs_id like 'suplido_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'bases_pymes_', 'bases_') where fs_id like 'bases_pymes_%' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'vat_code_chart_pymes_root', 'vat_code_chart_root') where fs_id = 'vat_code_chart_pymes_root' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'tax_group_both_pymes', 'tax_group_both') where fs_id = 'tax_group_both_pymes' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'tax_group_purchase_pymes', 'tax_group_purchase') where fs_id = 'tax_group_purchase_pymes' and module = 'account_es_pyme';
UPDATE ir_model_data set fs_id = REPLACE(fs_id, 'tax_group_sale_pymes', 'tax_group_sale') where fs_id = 'tax_group_sale_pymes' and module = 'account_es_pyme';
UPDATE ir_model_data SET module = 'account_es' WHERE module = 'account_es_pyme';
UPDATE ir_translation set module = 'account_es' where module = 'account_es_pyme';
UPDATE ir_ui_view set module = 'account_es' where module = 'account_es_pyme';
UPDATE ir_model_field set module = 'account_es' where module = 'account_es_pyme';
UPDATE ir_module set state = 'not activated' where name = 'account_es_pyme';
UPDATE ir_module set state = 'activated' where name = 'account_es';
DELETE from ir_module_dependency where name = 'account_es_pyme';
