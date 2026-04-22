# -*- coding: utf-8 -*-
{
    'name': "Automatic Database Backup",
    'summary': "Automatic Odoo Database Backup to Local Server, Remote Server, or Cloud Storage "
               "(Google Drive, Dropbox, OneDrive, Nextcloud, Amazon S3).",
    'description': """
    Automatic Odoo Database Backup
    ==============================

    This module enables automatic backup of your Odoo databases with flexible storage options:

    - Local server
    - Remote server (via SSH/SFTP)
    - Google Drive
    - Dropbox
    - OneDrive
    - Nextcloud
    - Amazon S3

    Key Features:
    -------------
    - Schedule automatic backups via cron jobs
    - Store backups securely in multiple locations
    - Receive backup notifications by email
    - Easy configuration from Odoo interface
    - Supports Odoo 16 and above

    Perfect for ensuring data safety and disaster recovery with cloud and on-premise backup support.
    """,
    'version': '1.0',
    'category': 'Extra Tools',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/db_backup_configure_views.xml',
        'wizard/dropbox_auth_code_views.xml',
    ],
    'external_dependencies': {
        'python': ['dropbox',
                   'pyncclient',
                   'boto3',
                   'nextcloud-api-wrapper',
                   'paramiko']
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
