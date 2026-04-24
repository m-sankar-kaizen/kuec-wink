# -*- coding: utf-8 -*-
{
    'name': "Requisition Quintuple Approvals",
    'summary': "Multi-level approval workflow and budget transfer integration for purchase requisitions",
    'description': """
        This module implements a robust five-level approval workflow for purchase requisitions,
        enabling comprehensive validation and control before purchase orders are created.
        It integrates budget transfer requests directly within the approval process,
        supports manual currency exchange rates, and extends vendor selection and purchase
        confirmation with custom wizards.

        Features include:
        - Multi-stage approval states with role-based validations.
        - Automated creation and management of budget transfer requests.
        - Enhanced purchase order creation with vendor and currency rate handling.
        - Integration with accounting, HR, and budget management modules.
        - Custom notifications and mail activity scheduling for approvals.
        - Detailed security groups and access control tailored for requisition approvals.

        Designed for organizations needing strict control over procurement spend and budget management.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': [
        'material_purchase_requisitions',
        'kz_budget_custom',
        'bi_manual_currency_exchange_rate',
        'kz_notification_base',
        'kaz_company_restriction_base'
    ],
    'data': [
        'security/approval_res_groups.xml',
        'security/payment_res_groups.xml',
        'security/ir.model.access.csv',
        'data/requisition_approval_line_ir_cron_data.xml',
        'data/mail_activity_type_data.xml',
        'data/transfer_request_ir_sequence_data.xml',
        'wizard/budget_transfer_wizard_views.xml',
        'wizard/purchase_confirmation_wizard_views.xml',
        'wizard/reject_warning_wizard_views.xml',
        'wizard/vendor_extension_wizard.xml',
        'views/material_purchase_requisition_views.xml',
        'views/budget_views.xml',
        'views/budget_transfer_request_views.xml',
        'views/res_users_views.xml',
        'views/account_payment_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
