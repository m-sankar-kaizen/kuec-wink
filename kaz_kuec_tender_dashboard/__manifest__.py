{
    'name': 'Tender Dashboard',
    'version': '1.0',
    'depends': [
        'kaz_vendor_management',
        'kaz_vendor_contact_company_restriction',
        'kaz_company_restriction_base',
    ],
    'data': [
        'views/tender_rfq_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_kuec_tender_dashboard/static/src/views/*.js',
            'kaz_kuec_tender_dashboard/static/src/views/*.xml',
        ],
    }
}
