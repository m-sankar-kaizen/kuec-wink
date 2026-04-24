{
    'name': 'End of Service',
    'summary': """
        End of Service
        This module manages end-of-service settlements for employees, including calculation,
        approvals, payslip generation, accounting, and reporting.
    """,
    'description': """
        End of Service Module

        This module provides a complete workflow for handling employee end-of-service settlements,
        integrated with payroll and HR operations. It automates the computation of the final
        settlement based on employee contract details, benefits, gratuity/pension rules,
        and unpaid leaves.

        Key Functionalities:
        - Multi-stage settlement approval (draft → confirm → approve)
        - Gratuity (for expat) and pension (for local) support
        - Payslip generation for settlement
        - Final journal entry creation
        - Integration with HR Contracts, Payroll, and Leaves
        - Custom salary structure support for EOS
        - Accounting enforcement for EOS-specific salary rules
        - Detailed reports and user access control via HR groups

        Designed specifically for government institutions in the UAE with localization support
        and compliance to institutional policies.

        Author: Kaizen Principles
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['kaz_employee_reports',
                'l10n_ae_hr_payroll',
                'hr_payroll_account'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/employee_settlement_sequence_data.xml',
        'data/pay_rule_data.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_employee_settlements_views.xml',
        'reports/hr_employee_settlements_report.xml',
        'views/end_of_service_actions.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
