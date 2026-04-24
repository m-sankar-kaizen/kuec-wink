# -*- coding: utf-8 -*-
{
    "name": "Kaizen - Cash Flow Forecasting",
    "version": "18.0.1.1",
    "author": "Kaizen Principles",
    "website": "http://www.kaizenae.com/",
    "category": "Accounting/Accounting",
    "summary": "Forecast Cash-In/Cash-Out by fiscal period with Opening/Net/Closing balances, dashboards, and forecast vs. actual analysis.",
    "description": """
Kaizen – Cash Flow Forecasting

Plan and monitor cash by day/week/month. Define forecast categories and types mapped to accounts/analytic accounts. 
Auto-calculate via past entries, past periods, pending AR/AP, or dependent types; or set fixed values. 
Includes wizarded generation, OWL dashboards (forecast vs. real), onboarding, reports/pivot/graph, 
multi-company security, and optional Budget Forecasting add-on.

Key features:
- Fiscal years & periods (daily/weekly/monthly)
- Forecast categories/types (Cash-In, Cash-Out, Opening, Net, Closing)
- Auto/manual methods (past entries, past periods, pending, dependent, fixed)
- Opening/Closing rollovers & Net computation
- Wizard to create/update forecasts and real values
- Dashboards & analysis views (pivot/graph/tree)
- Onboarding steps, security groups, multi-company rules
- Optional kaz_budget_forecasting integration
    """,
    "images": ["static/description/banner.gif"],
    "price": 380,
    "currency": "USD",
    'depends': ['account', 'sale', 'purchase'],
    'license': 'OPL-1',
    'sequence': 20,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/kaz_budget_forecasting_installation_wizard.xml',
        'data/onboarding_data.xml',
        'views/kaz_cash_forecast_group.xml',
        'views/kaz_cash_forecast_dashboard_menu.xml',
        'views/kaz_cash_forecast_type.xml',
        'views/cash_forecast_tag.xml',
        'views/res_config_settings.xml',
        'views/cash_forecast_fiscal_year.xml',
        'views/create_update_cash_forecast.xml',
        'views/kaz_cash_forecast.xml',
        'views/kaz_cash_forecast_report_view.xml',
        'views/account_account_view.xml',
        'views/local_account_book.xml',
        'data/kaz_cash_forecast_actual_value_cron.xml',
        'data/demo_data.xml',
        'views/kaz_budget_forecast_settings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_cash_flow_forecasting/static/src/js/kaz_kanban_chart.js',
            'kaz_cash_flow_forecasting/static/src/js/get_rule.js',
            'kaz_cash_flow_forecasting/static/src/js/kaz_cash_forecasting_dashboard.js',
            'kaz_cash_flow_forecasting/static/src/scss/main.scss',
            'kaz_cash_flow_forecasting/static/src/js/pivot.xml',
            'kaz_cash_flow_forecasting/static/src/xml/**/*',
        ],
        'web.assets_backend_lazy':[
            'kaz_cash_flow_forecasting/static/src/js/pivot.js',
        ],
    },
    'application': True,
    'post_init_hook': 'create_cash_forecast_type',
}
