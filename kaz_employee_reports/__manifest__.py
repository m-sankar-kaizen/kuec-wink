# -*- coding: utf-8 -*-
{
    'name': "Employee Reports",
    'summary': """
        Custom HR reporting tools and workflows for employee management at Kaizen.
    """,
    'description': """
        This module provides extended employee-related reporting features, HR workflows, 
        and custom document generation tools for handling employment letters, salary transfer letters, 
        health insurance requests, visa requests, resignation forms, and exit clearance processes.
        
        Key Features:
        - Employee employment & salary letters with bilingual formatting
        - Visa and health insurance request approval workflows (multi-level)
        - Exit interview & clearance report generation
        - Integration with employee master data (kaz_employees)
        - Print-ready PDF reports using customized QWeb templates
        - Role-based access groups for HR, managers, and HR teams
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employee',
    'version': '1.0',
    'depends': ['kaz_child_allowance',
                'kaz_arabic_translations',
                'kaz_ku_contract',
                'kaz_acting_allowance'
                ],
    'data': [
        'security/ankabut_letters.xml',
        'security/visa_request_groups.xml',
        'security/health_insurance_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_activity_type_data.xml',
        'reports/salary_transfer_letter_report.xml',
        'reports/employment_letter_report.xml',
        'reports/registeration_form_report.xml',
        'reports/exit_interview_report.xml',
        'reports/exit_clearance_report.xml',
        'reports/health_insurance_report.xml',
        'reports/visa_request_report.xml',
        'reports/salary_letter.xml',
        'views/employment_letter_views.xml',
        'reports/golden_visa_report.xml',
        'views/res_company_views.xml',
        'views/salary_transfer_letter_views.xml',
        'views/register_form_views.xml',
        'views/exit_clearance_views.xml',
        'views/exit_interview_views.xml',
        'views/health_insurance_views.xml',
        'views/hr_contract_views.xml',
        'views/visa_request_views.xml',
        'views/res_bank_views.xml',
        'views/address_to_views.xml',
        'views/salary_letter_views.xml',
    ],
    'assets': {
        'web.report_assets_pdf': [
            '/kaz_employee_reports/static/src/css/report_style.css',
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
