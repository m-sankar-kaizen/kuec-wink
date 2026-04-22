# -*- coding: utf-8 -*-
{
    'name': "HireSmart",
    'version': '18.0.0.0',
    'category': 'Services',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'pragtech.co.in',
    'summary': "Advanced HR module with Resume OCR, Hiring Workflow, JD Generator, Internal Job Posting",
    'description': """
        This module extends Odoo's recruitment with powerful HR features:

        - **Hiring Request & Approval Workflow** – Multi-step approval process for job requisitions. 
        - **Internal Job Posting (IJP)** – Allow internal employees to apply for open positions.  
        - **Auto-generated Job Summary** – AI-assisted job summary creation based on job post details.
        - **Resume OCR** – Automatically extracts candidate data from resumes using OCR.  

        The module streamlines talent acquisition, enhances collaboration.
    """,
    'depends': ['base', 'mail', 'hr_recruitment_skills'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_groups.xml',
        'wizard/wizard_resume_ocr_upload_view.xml',
        'views/inherit_res_config_settings_views.xml',
        'views/inherit_hr_applicant_views.xml',
        'views/resume_ocr_views.xml',
        'views/hiring_request_views.xml',
        'views/all_approvals_views.xml',
        'views/approval_to_review_view.xml',
        'views/internal_job_application_views.xml',
        'views/internal_job_post_views.xml',
        'views/ai_job_description.xml',
        'views/menu_root.xml',
    ],
    'maintainer': 'sales@pragtech.co.in',
    'images': ['static/description/hire_smart_front.gif'],
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=HireSmart',
    'price': 40.00,
    'currency': 'USD',
    'license': 'OPL-1',
    'application': True,
    'auto_install': False,
    'installable': True,
}
