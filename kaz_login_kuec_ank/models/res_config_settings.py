# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    """
    Inherits:
        Inherits from `res.config.settings` to extend the system configuration
        options accessible to administrators via the Settings interface.

    Purpose:
        Adds a configuration field (`hide_default_login`) that allows system
        administrators to enable or disable visibility of the default Odoo
        login screen.

    Use Case:
        This is particularly useful in institutional deployments (e.g., universities,
        enterprises, government portals) where Odoo is integrated with a custom
        authentication system such as:
            - Single Sign-On (SSO)
            - CAS / Shibboleth / LDAP
            - External portals or reverse proxies handling login

    Field(s):
        - hide_default_login (Boolean):
            - When True, the system parameter `kaz_login_kuec_ank.hide_default_login`
              is set.
            - This parameter can be used in custom controllers, middleware, or view logic
              to conditionally suppress or redirect away from `/web/login`.

    Notes:
        - This setting appears in the General Settings UI due to view inheritance
          from `base_setup.res_config_settings_view_form`.
        - The value is stored persistently in `ir.config_parameter`.
    """
    _inherit = 'res.config.settings'

    hide_default_login = fields.Boolean(
        string="Hide Default Login Page",
        config_parameter='kaz_login_kuec_ank.hide_default_login',
        help="""
        If enabled, the default Odoo login screen will be hidden.
        This is useful for deployments where a custom login mechanism or
        redirect flow (e.g., SSO, university portal) replaces the native login.
        """
    )
