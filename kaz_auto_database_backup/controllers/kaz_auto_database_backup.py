# -*- coding: utf-8 -*-
"""
Onedrive and Google Drive OAuth2 Callback Controller

This module defines public HTTP routes to handle OAuth2 callbacks from
OneDrive and Google Drive authentication for use in automated database backup
configurations. The controller uses the token received from the OAuth process
and updates the backup configuration accordingly.

Routes:
    - /onedrive/authentication: Handles OneDrive's OAuth2 callback.
    - /google_drive/authentication: Handles Google Drive's OAuth2 callback.

Author: Kaizen
"""

import json
from odoo import http
from odoo.http import request


class OnedriveAuth(http.Controller):
    """Controller for handling authentication with OneDrive and Google Drive."""

    @http.route('/onedrive/authentication', type='http', auth="public", csrf=False)
    def oauth2callback(self, **kw):
        """
        OAuth2 callback for OneDrive.

        This endpoint is called by Microsoft after successful user authentication.
        It retrieves the authorization code from the request, uses it to fetch
        access tokens, and updates the backup configuration accordingly.

        :param kw: A dictionary containing 'code' and 'state' from Microsoft OAuth2.
                   The 'state' is a JSON string containing:
                     - backup_config_id: ID of db.backup.configure record.
                     - url_return: Redirect URL after authentication.
        :return: A redirect response to the configured return URL.
        """
        state = json.loads(kw['state'])  # Parse the JSON-encoded state
        backup_config = request.env['db.backup.configure'].sudo().browse(state.get('backup_config_id'))
        backup_config.get_onedrive_tokens(kw.get('code'))  # Exchange code for tokens
        backup_config.hide_active = True  # Hide this config from user view
        backup_config.active = True       # Mark config as active
        return request.redirect(state.get('url_return'))

    @http.route('/google_drive/authentication', type='http', auth="public", csrf=False)
    def gdrive_oauth2callback(self, **kw):
        """
        OAuth2 callback for Google Drive.

        This endpoint is called by Google after successful user authentication.
        It retrieves the authorization code from the request, uses it to fetch
        access tokens, and updates the backup configuration accordingly.

        :param kw: A dictionary containing 'code' and 'state' from Google OAuth2.
                   The 'state' is a JSON string containing:
                     - backup_config_id: ID of db.backup.configure record.
                     - url_return: Redirect URL after authentication.
        :return: A redirect response to the configured return URL.
        """
        state = json.loads(kw['state'])  # Parse the JSON-encoded state
        backup_config = request.env['db.backup.configure'].sudo().browse(state.get('backup_config_id'))
        backup_config.get_gdrive_tokens(kw.get('code'))  # Exchange code for tokens
        backup_config.hide_active = True  # Hide this config from user view
        backup_config.active = True       # Mark config as active
        return request.redirect(state.get('url_return'))
