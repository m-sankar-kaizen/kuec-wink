{
    'name': "HR Menu Structure (KUEC)",
    'description': """
This module restructures the HR menus for Khalifa University Enterprises Company Limited (KUEC). 
It organizes all HR-related modules, such as employee management, payroll, loans, custody, 
performance management, offboarding, orientation, allowances, and memos, into a clear and 
logical menu structure for easier navigation and improved usability.
""",
    'summary': "Restructures HR menus for KUEC for better organization and navigation.",
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Hidden',
    'version': '1.0',
    'depends': [
        'kaz_kuec_letters', 'hr_custody', 'ent_ohrms_loan', 'kaz_child_allowance',
        'kaz_education_fees', 'kaz_kuec_offboarding', 'employee_orientation',
        'hrms_performance_management', 'hr_internship', 'kaz_kuec_employee_probation',
        'hr_appraisal', 'kaz_hr_memo_action', 'hr_holidays', 'hr_payroll',
        'kaz_bank_transfer', 'kaz_employee_performance_kuec', 'kaz_kuec_overall_doa_approval',
        'hr_employee_secondment', 'kaz_hr_employee_bonus', 'kaz_leave_entitlement_kuec',
    ],
    'data': [
        'security/groups.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
