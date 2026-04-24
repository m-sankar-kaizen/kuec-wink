{
    'name': 'Requisition Dashboard',
    'version': '1.0',
    'depends': [
        'material_purchase_requisitions',
        'kaz_vendor_contact_company_restriction',
        'kaz_company_restriction_base',
    ],
    'data': [
        'views/material_purchase_requisition_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_kuec_requisition_dashboard/static/src/views/*.js',
            'kaz_kuec_requisition_dashboard/static/src/views/*.xml',
        ],
    }
}
