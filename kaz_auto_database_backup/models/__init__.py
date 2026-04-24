# -*- coding: utf-8 -*-
"""
This module initializes the Automatic Database Backup feature.

It imports the `db_backup_configure` model, which manages backup configurations
for various destinations including local, FTP, SFTP, Google Drive, Dropbox,
OneDrive, Amazon S3, and NextCloud.

The `db_backup_configure` model handles:
- Credential storage and validation
- Token management (OAuth2 for cloud platforms)
- Connection testing
- Auto-cleanup of old backups
- Notification and scheduling

Usage:
    This module is intended to be part of an Odoo custom addon for scheduled
    database backup with multi-destination support.
"""

from . import db_backup_configure
