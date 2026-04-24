from odoo import models, fields


class HrCandidate(models.Model):
    _inherit = 'hr.candidate'

    interview_feedback_ids = fields.One2many('interview.feedback',
                                   'candidate_id',
                                   string='Interview Feedback')