# -*- coding: utf-8 -*-
{
    "name": "Inter Company Payments",
    "version": "18.0.1.0.0",
    "summary": "",
    "description": """  """,
    "sequence": 10,
    "author": "Kaizen Principals",
    "license": "OPL-1",
    "depends": ["base",
                "account",
                "account_accountant",
                'kaz_company_restriction_base',
                "wps_reports"],
    "external_dependencies": {
        "python": ["num2words"]
    },
    "data": [
        'security/ir.model.access.csv',
        'reports/report_voucher.xml',
        'reports/ir_actions_report.xml',
        'wizard/account_payment_register.xml',
        'views/res_company.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/account_move_line_reconcile_custom.xml',
    ],
}
