# -*- coding: utf-8 -*-
{
    'name': "PR and PO Ageing Management",
    'summary': "Manage ageing and reminders for Purchase Requests (PRs) and Purchase Agreements (PAs)",
    'description': """
    This module provides automated management for Purchase Requests (PRs) and Purchase Agreements (PAs) approaching fiscal year-end or expiry. 
    It includes:

    - Notifications to responsible users X days before fiscal year-end for draft PRs and PAs.
    - Automatic cancellation of PRs and PAs if no action is taken by year-end.
    - Ability to request carry-over for PRs or extend agreements before expiry.
    - Wizard interface for requesting agreement extensions.
    - Tracking and messaging for all ageing, extension, and cancellation actions.
    - Access control for users based on roles and company.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': ['kaz_vendor_management', 'account', 'purchase_requisition'],
    'data': [
        'data/pr_ir_cron_data.xml',
        'data/pa_ir_cron_data.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/material_purchase_requisition_views.xml',
        'views/purchase_requisition_views.xml',
        'views/res_config_settings_views.xml',
        'views/extend_agreement_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
