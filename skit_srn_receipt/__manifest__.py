# -*- coding: utf-8 -*-
{
    'name': 'Service Receipt Tracker',
    'summary': 'Create receipt and back order for service product',
    'description': """ To create a receipt in service type product and create
                        back order in done quantity is less than received /
                        quantity""",
    'author': 'Kaizen Principles',
    'website': 'http://www.kaizenae.com',
    'version': '1.0',
    'category': 'Purchase',
    'depends': ['purchase_stock'],
    'data': [
        'data/service_request_ir_sequence_data.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'wizard/service_backorder_confirmation_views.xml',
        'views/purchase_order_views.xml',
        'views/service_receipt_views.xml',
        'views/service_receipt_line_views.xml',
        'reports/service_receipt_report.xml',
        'reports/service_completion_report.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
}
