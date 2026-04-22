# -*- coding: utf-8 -*-
{
    'name': "Overall DOA Approval (KUEC)",
    'summary': "Manage and automate Delegation of Authority (DOA) approvals for HR, Procurement, and Internship processes",
    'description': """
    Overall DOA Approval (KUEC)

    This module centralizes and automates the Delegation of Authority (DOA) approval processes within KUEC.
    It covers multiple workflows including:

    - HR Applicant approvals
    - Internship Reward approvals
    - Financial Awards and Bonuses
    - Recruitment staffing plan approvals
    - Offboarding approvals

    Key Features:
    - Multi-level approval workflow based on user roles (Employee, HOD, Finance, CCOE, CEO, Board)
    - Integration with HR, Recruitment, Internship, and Procurement modules
    - Activity assignment and notifications for approvers
    - Access control enforced via groups and model-level permissions
    - Comprehensive views for managers and employees
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Hidden',
    'version': '1.0',
    'depends': [
        'kaz_kuec_offboarding', 'kaz_procurement_doa_kuec',
        'kaz_kuec_recruitment_staffing_plan', 'hr_internship',
        'kaz_related_party_balances', 'bi_manual_currency_exchange_rate',
        'expense_funding', 'kaz_kuec_master_budget', 'account_asset',
        'kaz_employee_promotion', 'kaz_kuec_leasing',
        'kaz_recruitment'
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/res_groups.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'views/register_form_views.xml',
        'views/hr_master_plan_views.xml',
        'views/res_config_settings_views.xml',
        'views/register_form_approval_views.xml',
        'views/hr_master_plan_approval_views.xml',
        'views/hr_recruitment_stage_views.xml',
        'views/hr_applicant_view.xml',
        'views/hr_applicant_approval_views.xml',
        'views/hr_internship_reward_views.xml',
        'views/hr_internship_reward_approval.xml',
        'views/related_party_entries_views.xml',
        'views/related_party_entries_approval_views.xml',
        'views/write_off_request_views.xml',
        'views/write_off_request_approval_views.xml',
        'views/account_move_views.xml',
        'views/account_move_approval_views.xml',
        'views/account_payment_views.xml',
        'views/petty_cash_request_views.xml',
        'views/petty_cash_request_approval_views.xml',
        'views/credit_card_request_views.xml',
        'views/credit_card_request_approval_views.xml',
        'views/account_asset_views.xml',
        'views/account_asset_depreciation_views.xml',
        'views/account_asset_depreciation_approval_views.xml',
        'views/budget_analytic_views.xml',
        'views/budget_master_plan_views.xml',
        'views/budget_master_plan_approval_views.xml',
        'views/settlement_request_views.xml',
        'views/settlement_request_approval_views.xml',
        'views/employee_promotion_approval_views.xml',
        'views/employee_promotion_views.xml',
        'views/lease_lessee_contract_views.xml',
        'views/lease_lessee_contract_approval_views.xml',
        'views/lease_lessor_contract_views.xml',
        'views/lease_lessor_contract_approval_views.xml',
        'wizards/account_payment_register_views.xml',
        'wizards/asset_modify_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
