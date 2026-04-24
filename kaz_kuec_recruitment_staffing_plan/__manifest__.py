{
    'name': "KUEC Staffing Plan",
    'depends': [
        'base',
        'web',
        'hr',
        'hr_recruitment',
        'account_budget',
        'kaz_company_restriction_base',
        'kz_requisition_quintuple_approvals'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/email_template.xml',
        'data/sequence.xml',
        'views/hr_staffing_plan_views.xml',
        'views/res_settings_views.xml',
        'views/res_users_views.xml',
        'views/off_cycle_staffing_reason_views.xml',
        'views/hr_recruitment_requests_views.xml',
        'views/hr_job_position_request_views.xml',
        'views/hr_master_staffing_plan_views.xml',
        'views/hr_applicant_views.xml',
        'views/hr_employee_views.xml',
        'views/budget_line_views.xml',
        'views/menu.xml'
    ]
}
