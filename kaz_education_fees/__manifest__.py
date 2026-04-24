# -*- coding: utf-8 -*-
{
    'name': "Education Fees",
    'summary': "Manages employee children's education fee reimbursements and approvals",
    'description': """
Education Fees Management

This module handles the end-to-end workflow of employee children's education fee reimbursements, including:
- Multi-level approvals (HR team, HR manager)
- Custom salary rules for book/transport/tuition/other allowances
- Academic data management (School, Year, Grade)
- Integration with HR contracts and payroll
- Validation, refusal, and documentation tracking
""",
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employee',
    'version': '1.0',
    'depends': ['ent_ohrms_loan'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_refusal_data.xml',
        'data/mail_activity_type_data.xml',
        'data/education_fees_ir_sequence_data.xml',
        'views/education_fees_actions.xml',
        'views/education_fees_views.xml',
        'views/res_school_views.xml',
        'views/academic_year_views.xml',
        'views/academic_grade_views.xml',
        'views/hr_grade_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
