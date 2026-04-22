{
    'name': 'KUEC Grade Structure',
    'depends': [
        'kaz_company_restriction_base',
        'hr_payroll',
        'hr_contract',
        'kaz_employees',
        'kaz_annual_air_ticket'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/kuec_grade_views.xml',
        'views/hr_job_views.xml',
        'views/hr_payslip_views.xml',
    ]
}
