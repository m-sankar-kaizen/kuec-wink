{
    'name': 'Kaz Kuec Offboarding',
    'depends': [
        'kaz_employee_reports',
        'kaz_end_of_service',
        'hr_custody',
        'expense_funding',
        'kaz_ent_loan',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'data/pay_rule_data.xml',
        'views/resignation_form_views.xml',
        'views/exit_interview_views.xml',
        'views/exit_clearance_views.xml',
        'views/employee_settlements_views.xml',
        'views/res_settings.xml',
    ]
}
