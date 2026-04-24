{
    'name': 'Advanced HR-LinkedIn Integration',
    'summary': "Seamless LinkedIn Integration for HR Recruitment",
    'description': """
    Integrate Odoo HR Recruitment with LinkedIn to streamline job posting, candidate sourcing,
    and social engagement. This module allows you to post open positions directly from Odoo
    to LinkedIn, track likes/comments on each post, and centralize your entire recruitment
    process. Ideal for businesses looking to optimize HR workflows and enhance employer branding.
    """,
    'category': 'Generic Modules/Human Resources',
    'version': "18.0.1.0.0",
    'depends': ['hr_recruitment', 'auth_oauth'],
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': "http://www.kaizenae.com/",
    'data': [
        'data/auth_linkedin_data.xml',
        'security/ir.model.access.csv',
        'views/recruitment_config_settings.xml',
        'views/hr_job_linkedin_likes_comments_views.xml',
        'views/linkedin_comments_views.xml',
        'views/oauth_views.xml',
    ],
    'external_dependencies':
        {
        'python': ['mechanize', 'linkedin'],
        },
    'images': ['static/description/banner.gif'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
