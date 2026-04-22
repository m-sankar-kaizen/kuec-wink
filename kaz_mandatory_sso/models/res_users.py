# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    """
    Extends the `res.users` model to support Single Sign-On (SSO) integration
    by assigning a preferred SSO method and linking users to SSO provider configurations.

    Fields Added:
        - sso_type (Selection):
            Determines which SSO method is applicable for the user. Options:
                * 'saml' - SAML 2.0 (e.g., Ankabut)
                * 'oauth' - OAuth2 (e.g., Google, KUEC)
        - saml_id (Many2one to auth.saml.provider):
            Foreign key to the SAML identity provider this user is assigned to.
        - oauth_id (Many2one to auth.oauth.provider):
            Foreign key to the OAuth2 provider this user is assigned to.

    Usage:
        - When a user has `sso_type = 'saml'`, the `saml_id` must be valid and
          configured under the correct provider tab (cross-referenced against
          allowed linked providers).
        - Admins can configure which authentication backend applies to each user.
        - Validation constraints are enforced to prevent inconsistent assignments.

    Related:
        - See `auth.saml.provider` and `auth.oauth.provider` for actual SSO configuration.
    """
    _inherit = 'res.users'

    show_sso_type = fields.Boolean(
        compute="compute_show_sso")

    @api.depends('groups_id')
    def compute_show_sso(self):
        for rec in self:
            if rec.has_group('base.group_user'):
                rec.show_sso_type = True
            else:
                rec.show_sso_type = False

    sso_type = fields.Selection([
        ('saml', 'SAML (Ankabut)'),
        ('oauth', 'OAUTH (KUEC)'),
    ], string="SSO Type", help="Select the SSO authentication type for the user.")

    saml_id = fields.Many2one('auth.saml.provider', string="SAML Provider",
                               help="Link to the SAML Identity Provider (e.g., Ankabut) for this user.")

    oauth_id = fields.Many2one('auth.oauth.provider', string="Authentication Provider",
                                help="Link to the OAuth Provider (e.g., Google, KUEC) for this user.")

    @api.constrains('saml_id', 'sso_type')
    def _check_sso_type_requirements(self):
        """
        Validates that if the user selects SAML as the SSO method, the specified SAML provider
        (`saml_id`) is one of the valid providers linked to this user via the many2many relation
        `saml_ids.saml_provider_id`.

        Raises:
            ValidationError: If a SAML provider is manually set without being registered
            under the user's valid SAML providers, ensuring consistency and security in SSO mapping.
        """
        for rec in self:
            if rec.sso_type == 'saml' and rec.saml_id:
                if rec.saml_id.id not in rec.saml_ids.saml_provider_id.ids:
                    raise ValidationError("Provide the SAML details under SAML tab.")
