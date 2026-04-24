# -*- coding: utf-8 -*-
{
    'name': "PDP SRN KUEC (Company Customization)",
    'summary': "Adds SRN and Down Payment functionality customized for KUEC",
    'description': """
    This module customizes the Purchase Order process for KUEC by providing:
    - SRN (Service Receipt Note) management
    - Down Payment options on Purchase Orders
    - Company-specific restrictions and settings
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['kaz_purchase_down_payment', 'srn_reciept_kaizen',
                'kaz_company_restriction_base',
                'kaz_vendor_management', 'kaz_kuec_report_base'],
    'data': [
        'data/paper_format_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'reports/service_completion_report.xml',
        'reports/purchase_order_report.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/service_receipt_views.xml',
        'views/srn_report_template_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/purchase_order_advance_payment_view.xml',
        'wizards/service_backorder_confirmation_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
