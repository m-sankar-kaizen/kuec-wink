from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    credit_control_warning_limit = fields.Float()


class Configuration(models.TransientModel):
    _inherit = 'res.config.settings'

    company_credit_control_warning_limit = fields.Float(
        related='company_id.credit_control_warning_limit', readonly=False
    )
