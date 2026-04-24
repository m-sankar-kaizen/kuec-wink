# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Secondment',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manage employee secondments with dynamic configuration',
    'description': """
        Employee Secondment Management
        ================================
        
        This module provides comprehensive secondment management features:
        
        * Temporary assignment of employees to higher-grade positions
        * Dynamic configuration for all business rules (durations, allowances, grades)
        * Automatic eligibility validation based on grade differences
        * Configurable allowance calculation (threshold and percentage)
        * One active secondment per employee restriction
        * Extension management with configurable limits
        * Automatic notifications before secondment end
        * Complete secondment history tracking
        * Performance monitoring integration
        
        All settings are configurable through HR Settings without code changes.
    """,
    'author': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'hr',
        'hr_contract',
        'hr_payroll',
        'mail',
        'kaz_kuec_grade_structure'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/hr_payroll_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_secondment_views.xml',
        'views/hr_employee_views_inherit.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_secondment_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
