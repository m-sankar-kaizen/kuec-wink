{
    'name': "KUEC Spreadsheet dashboard for accounting",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'account_reports'],
    'data': [
        "data/dashboards.xml",
        # "data/cron.xml",
        # "views/hr_employee_views.xml",
    ],
    'installable': True,
    'auto_install': ['account_reports'],
    'license': 'OEEL-1',
}
