# -*- coding: utf-8 -*-
{
    'name': "Procurement DOA (KUEC)",
    'summary': "Special Delegation of Authority for procurement approvals in KUEC",
    'description': """
    This module implements a special Delegation of Authority (DOA) workflow for KUEC company.
    It manages multi-level approvals for Material Purchase Requisitions based on KUEC's organizational structure,
    including Department Head, Finance & Procurement Head, CCOE, CEO, and KUEC Board.
    The module ensures proper notifications, approval tracking, and access rights for each level.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': ['kaz_pr_and_po_ageing_management', 'kaz_company_restriction_base',
                'kaz_approval_sign_base', 'po_confirm_restrictions', 'skit_srn_receipt',
                'kaz_research_and_development'
                ],
    'data': [
        'security/res_groups.xml',
        'security/material_purchase_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/material_purchase_requisition_views.xml',
        'views/budget_transfer_request_views.xml',
        'views/material_purchase_requisition_approval_views.xml',
        'views/budget_transfer_request_approval_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_order_approval_views.xml',
        'views/purchase_requisition_views.xml',
        'views/purchase_requisition_approval_views.xml',
        'views/purchase_contract_agreement_approval_views.xml',
        'views/purchase_contract_agreement_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_procurement_doa_kuec/static/src/**/*'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
