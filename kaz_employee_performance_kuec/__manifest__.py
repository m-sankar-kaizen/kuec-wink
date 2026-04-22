# -*- coding: utf-8 -*-
{
    'name': "Employee Performance Evaluation (KUEC)",
    'summary': "Manage employee performance, goals, and improvement plans for KUEC.",
    'description': """
This module allows KUEC to evaluate employee performance effectively. 
Features include:
- Configurable evaluation categories and methods
- Goal templates and tracking
- Performance improvement plans
- Survey integration for feedback collection
- Customizable settings per company
- Access control for managers and HR personnel
""",
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employees',
    'version': '1.0',
    'depends': ['kaz_procurement_doa_kuec', 'hr', 'account_accountant', 'survey'],
    'data': [
        'data/ir_cron_data.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/performance_evaluation_views.xml',
        'views/goal_modified_reason_views.xml',
        'views/evaluation_category_views.xml',
        'views/evaluation_method_views.xml',
        'views/goal_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/performance_improvement_plan_views.xml',
        'views/survey_survey_views.xml',
        'views/year_year_view.xml',
        'views/perormance_goal_line_views.xml',
        'views/performance_dashboard_action.xml',
        'wizards/choose_survey_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js',
            'kaz_employee_performance_kuec/static/src/**/*'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
