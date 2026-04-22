# -*- coding: utf-8 -*-
"""
Authentication wizard for setting up Dropbox integration with the database
backup configuration system in Odoo.

This transient model is triggered from the backup configuration form view and
used to:
- Generate and show the Dropbox authentication URL to the user
- Accept the authorization code from Dropbox
- Trigger refresh token generation and store it in the backup config record
"""
from werkzeug import urls
from odoo import api, fields, models, _

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'


class AuthenticationWizard(models.TransientModel):
    """
    Wizard to handle Dropbox OAuth2 authentication for backup configuration.

    This wizard is used to:
    - Display the Dropbox authentication URL to the user
    - Accept the authorization code provided after Dropbox login
    - Exchange the code for a refresh token and update the main configuration

    It only operates on the active backup configuration (`db.backup.configure`)
    record passed via context.
    """
    _name = 'dropbox.auth.code'
    _description = 'Authentication Code Wizard'

    dropbox_authorization_code = fields.Char(
        string='Dropbox Authorization Code',
        help='Authorization code provided by Dropbox after successful login.')

    dropbox_auth_url = fields.Char(
        string='Dropbox Authentication URL',
        compute='_compute_dropbox_auth_url',
        help='Computed Dropbox URL for user to authenticate and retrieve code.')

    @api.depends('dropbox_authorization_code')
    def _compute_dropbox_auth_url(self):
        """
        Compute the Dropbox authentication URL for the current backup config.

        This URL will be shown in the wizard for the user to access Dropbox
        login and get an authorization code.

        Context must contain `active_id` pointing to a db.backup.configure record.
        """
        backup_config = self.env['db.backup.configure'].browse(
            self.env.context.get('active_id'))
        dropbox_auth_url = backup_config.get_dropbox_auth_url()
        for rec in self:
            rec.dropbox_auth_url = dropbox_auth_url

    def action_setup_dropbox_token(self):
        """
        Finalize Dropbox OAuth setup by exchanging the auth code for a refresh token.

        This method will:
        - Mark the backup config record as active
        - Store the refresh token using the provided auth code
        - Hide the active toggle (set `hide_active = True`)

        :raises ValidationError: if the token exchange fails internally.
        """
        backup_config = self.env['db.backup.configure'].browse(
            self.env.context.get('active_id'))
        backup_config.hide_active = True
        backup_config.active = True
        backup_config.set_dropbox_refresh_token(self.dropbox_authorization_code)
