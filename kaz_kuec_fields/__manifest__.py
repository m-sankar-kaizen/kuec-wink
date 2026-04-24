{
    'name': 'Hide/ Show some fields specific to KUEC',
    'depends': [
        'kaz_company_restriction_base',
        'kaz_annual_air_ticket',
        'hr',
        'kaz_employees',
        'material_purchase_requisitions',
        'hr_employee_updation',
        'hr_holidays',
        'ank_payslip_report'
    ],
    'data': [
        'views/hr_employees.xml',
        'views/hr_leave_views.xml',
        'views/hr_payslip_views.xml',
        'reports/kuec_payslip_report.xml',
    ]
}
