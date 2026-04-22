from odoo import models, fields


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    available_in_portal = fields.Boolean()
