from odoo import models, fields


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    allow_interview = fields.Boolean(
        related='stage_id.allow_interview'
    )
    feedback_ids = fields.One2many('interview.feedback',
                                   'applicant_id',
                                   string='Interview Feedback')

    def change_state(self):
        if not self.allow_interview:
            return super(HrApplicant, self).change_state()
        elif self.allow_interview and not self._context.get('from_submit'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Interview Feedback',
                'res_model': 'interview.feedback',
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'kaz_kuec_recruitment_interview.interview_feedback_view_form_popup'
                ).id,
                'target': 'new',
                'context': {
                    'default_candidate_id': self.candidate_id.id,
                    'default_job_id': self.job_id.id if self.job_id else False,
                    'default_user_id': self.env.user.id,
                    'default_applicant_id': self.id,
                    'default_interview_date': fields.Date.today(),
                }
            }
        else:
            return super(HrApplicant, self).change_state()


