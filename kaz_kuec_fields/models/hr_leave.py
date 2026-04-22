from odoo import models, fields


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    company_code = fields.Selection(
        related='employee_company_id.company_code')
