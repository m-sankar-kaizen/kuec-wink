from odoo import models, fields


class Project(models.Model):
    _inherit = "project.project"

    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
