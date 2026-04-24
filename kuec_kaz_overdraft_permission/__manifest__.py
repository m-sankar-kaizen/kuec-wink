{
    'name': 'Overdraft Permission',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Manage overdraft permissions for liquidity accounts',
    'description': """
        This module adds an option to enable or disable overdraft (negative balance)
        on liquidity accounts (Bank and Cash).
    """,
    'depends': ['account'],
    'data': [
        'security/security.xml',
        'views/res_partner.xml',
        'views/account_move.xml',
        'views/account_account_views.xml',
        'views/res_config_settings.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
