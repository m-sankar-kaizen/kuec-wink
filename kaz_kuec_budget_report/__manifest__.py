{
    'name': 'Budget Report Extension',
    'depends': [
        'account_budget',
        'kaz_kuec_recruitment_staffing_plan',
        'kz_budget_custom',
        'kaz_budget_line_progress',
        'kaz_kuec_master_budget',
        'kz_requisition_quintuple_approvals'
    ],
    'data': [
        'reports/budget_report_views.xml',
    ]
}
