{
    'name': 'Force Email From',
    'version': '1.0',
    'summary': "Enforces fallback sender email to prevent outgoing mail failures.",
'description': """
This module enhances the default Odoo email sending mechanism by ensuring that all outgoing emails have a valid sender address.

Key Features:

• Automatically assigns a fallback email address if `email_from` is missing.
• Prioritizes the SMTP username configured on the outgoing mail server.
• Falls back to company email or user email if necessary.
• Prevents email sending failures caused by missing sender configuration.
• Improves mail delivery reliability without requiring manual system parameter setup.

This ensures stable and consistent email behavior across all outgoing messages.
""",
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Technical',
    'depends': ['mail'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
