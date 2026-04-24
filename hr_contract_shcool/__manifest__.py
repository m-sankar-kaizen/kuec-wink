# __manifest__.py
{
    'name': 'Payslip Reports (Educational Fees and Annual Ticket)',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': """
        Adds detailed educational fees management and annual ticket processing to employee contracts
        and payroll runs. Includes Excel report generation for education fee history and annual ticket data.
    """,
    'description': """
        This module extends the standard HR Contract and Payroll functionality to support detailed tracking 
        and reporting of employee child educational fees as well as annual ticket allowances.

        Features:
        - Adds child contract lines linked to HR contracts for recording educational fee details such as:
          child name, birth date, school, academic year, tuition fees, book fees, transportation, amount requested,
          amounts paid, and entitlement.

        - Extends HR Contract with fields for annual ticket details including ticket amounts for adults, children, infants,
          counts of family members, assignment details, financial summaries, and historical ticket data.

        - Adds two Excel report generators accessible from the Payslip Run form:
          1. Educational Fees History Report: Generates an Excel workbook listing all child education fee details
             linked to employees in the payroll run.
          2. Annual Ticket Process Report: Generates a comprehensive Excel report summarizing annual ticket
             allowances, employee assignment info, payment details, and outstanding amounts.

        - User interface enhancements including new tabs in HR Contract form for managing education fees and annual tickets.

        - Utilizes the 'openpyxl' Python library to create and style Excel reports for easy export and sharing.

        Use Cases:
        - HR teams managing employee benefits related to children’s education.
        - Payroll departments processing annual ticket allowances and tracking related payments.
        - Management requiring detailed, exportable reports for auditing and budgeting.

        Dependencies:
        - Requires installation of 'openpyxl' Python package.
        - Depends on Odoo HR, Payroll, and related custom modules like 'kaz_employees' and 'wps_reports'.

        Author: Kaizen Principles
        Website: https://www.kazinae.com
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kazinae.com",
    'depends': ['hr_payroll', 'wps_reports'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_child_contract_line_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_contract_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
