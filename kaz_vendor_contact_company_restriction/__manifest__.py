# -*- coding: utf-8 -*-
{
    'name': "Vendor Contact Company Restriction",
    'summary': "Restricts Vendor, PR, and R&D features specifically for the KUEC company entity.",
    'description': """
            Vendor Contact & Purchase Requisition Restrictions for KUEC
            ===========================================================

            This module implements specific access control and restrictions for the KUEC company context.

            Key Features:
            -------------
            * **Vendor Restrictions:** Limits specific features or visibility on Partner/Vendor contacts when associated with KUEC.
            * **Purchase Requisitions (PR):** Enforces company-specific logic and restrictions on Material Purchase Requisitions for KUEC.
            * **R&D Integration:** Applies restrictions to Research & Development views in relation to KUEC protocols.

        """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': ['kaz_procurement_doa_kuec', 'kaz_research_and_development',
                'department_procurement', 'bi_manual_currency_exchange_rate',
                'kaz_pr_and_po_ageing_management', 'kaz_flexible_working_hours',
                'kz_requisition_quintuple_approvals',
                ],
    'data': [
        'views/res_partner_views.xml',
        'views/material_purchase_requisition_views.xml',
        'views/research_development_views.xml',
        'views/budget_transfer_request_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/purchase_requisition_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_requisition_type_views.xml',
        'views/resource_calendar_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
