from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'

    kuec_grade_id = fields.Many2one('kuec.grade',
                                    string="KUEC Grade")
    company_code = fields.Selection(
        related='company_id.company_code')
