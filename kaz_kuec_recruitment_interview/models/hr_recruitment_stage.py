from odoo import models, fields


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    allow_interview = fields.Boolean(
        string='Allow Interview Scheduling', default=False)
