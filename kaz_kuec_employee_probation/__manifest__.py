{
    'name': "KUEC Employee Probation",
    'depends': ['hr',
                'kaz_employees',
                'hr_internship',
                'kaz_kuec_offboarding'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/res_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'wizards/extend_probation.xml',
        'views/hr_internship_feedback_views.xml',
        'views/employee_probation_menu.xml',
    ]
}
