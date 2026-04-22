# -*- coding: utf-8 -*-
from odoo.addons.auth_signup.controllers.main import Home
from odoo import http
from odoo.http import request


class HomePage(Home):
    """
    Custom login controller extending Odoo's auth_signup Home controller.

    Purpose:
    --------
    This class overrides the default web login behavior to dynamically control
    whether the standard username/password login form should be visible or hidden
    on the login page, based on a system configuration parameter.

    Configuration:
    --------------
    The visibility of the default login form is controlled by the system parameter:
    - key: 'kaz_login_kuec_ank.hide_default_login'
    - value: Boolean (string 'True' or 'False')

    If set to 'True', the standard login form (username/password) will be hidden from the UI.

    Use Cases:
    ----------
    - When using external authentication (SAML, LDAP, OAuth) and wanting to hide the default login
    - Branding or security reasons to disable login form conditionally
    """

    @http.route()
    def web_login(self, *args, **kw):
        """
        Override the default /web/login controller route.

        Adds a new QWeb context variable 'hide_default_login' which can be used
        in the login page template to conditionally show/hide the login form.

        Returns:
            werkzeug.wrappers.Response: HTTP response object including the
            rendered login page with additional context.
        """
        # Call original web_login logic from auth_signup
        response = super().web_login(*args, **kw)

        # Inject custom QWeb context variable based on system parameter
        response.qcontext['hide_default_login'] = request.env[
            'ir.config_parameter'
        ].sudo().get_param('kaz_login_kuec_ank.hide_default_login')
        return response
