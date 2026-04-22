# -*- coding: utf-8 -*-
{
    'name': 'HR Payroll Extension',
    'version': '1.0',
    'summary': """Extend Odoo Payroll with streamlined 
    enhancements based on Kaizen principles.""",
    'description': """
        HR Payroll Extension - Kaizen-Driven Enhancement

        This module enhances the default HR Payroll functionalities
         in Odoo by introducing 
        clean, continuous improvements based on **Kaizen principles**:

        ▶ Continuous Improvement:  
           Modular and maintainable payroll enhancements
            added without disrupting core flows.

        ▶ Eliminate Waste:  
           Simplifies payroll processes, reduces redundancy,
            and automates repetitive tasks.

        ▶ Standardize Workflows:  
           Introduces reusable payroll structures, rules,
            and patterns for HR departments.

        ▶ Empower Employees:  
           Enhances transparency in payroll data and 
           supports scalable HR systems.

        ▶ Quality First:  
           Structured codebase with clear XML/record 
           definitions and compliant structure types.

        Key Features:
        - Adds default salary structure: Regular Pay
        - Associates unpaid leave work entry exclusion
        - Multi-country compatible design
        - Foundation for further rule and contribution table extension

        Ideal for:
        - Organizations looking for incremental payroll improvements
        - HR teams applying lean methodology to payroll
        - Developers extending or localizing payroll by country

        For more info or support, visit our website.
    """,
    'category': 'Human Resources/Payroll',
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'support': 'Kaizen Principles',
    'depends': ['hr_payroll'],
    'data': [
        'data/hr_payroll_structure_data.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
