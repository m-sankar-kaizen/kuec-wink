{
    'name': 'Kaizen Credit Card Reports',
    'depends': [
        'expense_funding'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/credit_card_report_wizard_views.xml',
        'reports/credit_card_report.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'kaz_kuec_credit_card_reports/static/src/js/action_manager.js'
            ],
        },
}
