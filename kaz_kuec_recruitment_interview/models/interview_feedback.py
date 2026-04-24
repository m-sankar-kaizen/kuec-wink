from odoo import models, fields


class InterviewStages(models.Model):
    _name = 'interview.feedback'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Interview Feedback'
    _rec_name = 'candidate_id'

    candidate_id = fields.Many2one('hr.candidate')
    interview_date = fields.Date(string='Interview Date')
    job_id = fields.Many2one('hr.job')
    user_id = fields.Many2one('res.users', string='Interviewer')
    rating = fields.Selection(
        [('0', 'Nil'), ('1', 'Poor'), ('2', 'Average'), ('3', 'Good'),
         ('4', 'Very Good'), ('5', 'Excellent')], string='Overall Rating')

    feedback = fields.Html(string='Feedback')

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')

    def submit(self):
        self.applicant_id.with_context(
            from_submit=True
        ).change_state()
