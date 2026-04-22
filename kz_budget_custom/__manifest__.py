# -*- coding: utf-8 -*-
{
    'name': "Budget Customizations",
    'summary': """
        Department-based Budgeting with Absolute Values, Analytics, and Auto Budget Creation.
    """,
    'description': """
        This module extends Odoo's standard budgeting features (`account_budget`) to support:

        - Department-wise budget assignment and automatic budget creation upon 
        department creation.
        - Masked budget line values (absolute planned, theoretical, and practical
         amounts) for clear UI representation.
        - Expense tagging and control for planned amounts.
        - Auto-assignment of analytic accounts to departments.
        - Auto-linking department's analytic account to budget lines.
        - Computation and display of total planned, practical, and theoretical 
        amounts on the budget.
        - UI enhancements to budget and department forms including stat buttons
         and subtotals.

        Ideal for organizations that need to:
        - Enforce departmental budget visibility.
        - Simplify planning vs. actual tracking.
        - Separate UI display from backend signed logic (positive/negative values).

        This module builds on top of:
        - `account_budget`
        - `hr`
        - `analytic`
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Accounting/Budget',
    'version': '1.0',
    'depends': ['account_budget',
                'kaz_company_restriction_base',
                'hr',
                'analytic'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/account_analytic_plan_data.xml',
        'views/account_budget_post_views.xml',
        'views/budget_analytic_views.xml',
        'views/hr_department_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
