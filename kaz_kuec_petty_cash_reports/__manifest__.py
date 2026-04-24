{
    'name': 'Kaizen Petty Cash Reports',
    'depends': [
        'expense_funding'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/petty_cash_report_wizard_views.xml',
        'reports/petty_cash_report.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'kaz_kuec_petty_cash_reports/static/src/js/action_manager.js'
            ],
        },
}
