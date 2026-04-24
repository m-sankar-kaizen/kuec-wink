{
    'name': 'KAZ KUEC Report Updates',
    'depends': ['account',
                'kaz_vendor_management',
                'kaz_company_restriction_base',
                'kaz_employees',
                'l10n_gcc_invoice',
                'kaz_kuec_overall_doa_approval'],
    "external_dependencies": {
        "python": ["num2words"]
    },
    'data':
        [
            'views/report_invoice.xml',
            'views/res_company_views.xml',
            'views/report_payment_receipt_templates.xml'
         ]
}
