{
    'name': "KUEC Recruitment Interview",
    'version': '18.0.1.0.0',
    'category': 'Hr',
    'summary': 'KUEC Recruitment Interview',
    'description': """KUEC Recruitment Interview""",
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'kaz_kuec_recruitment_process',
        'kaz_recruitment'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_applicant_views.xml',
        'views/hr_candidate_views.xml',
        'views/interview_feedback_views.xml',
        'views/hr_recruitment_stage_views.xml',
        'views/menu.xml'
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
