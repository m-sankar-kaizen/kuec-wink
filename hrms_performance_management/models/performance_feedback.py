from odoo import models, fields, _, api
from datetime import date
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)




class PerformanceFeedback(models.Model):
    _name = 'performance.feedback'
    _description = 'Performance Feedback'

    name = fields.Char(string='Sequence',copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    evaluation_id = fields.Many2one('hrms.evaluation', string="Evaluation Reference", readonly=True)
    hr_comment = fields.Text(string="HR Comment")
    parent_id = fields.Many2one('hr.employee',string="Manager", readonly=True)
    state = fields.Selection([('new','New'),('submitted','Submitted'),('reviewed','Reviewed'),('approved','Approved'),('done','Done')],default="new")
    feedback360_ids = fields.One2many('hrms.feedback360','performance_feedback_id', string="360 Feedback")
    goal_id = fields.Many2one('my.goals', string="Goal", readonly=True)
    outcome_decision = fields.Selection([
        ('high', 'High Performer'),
        ('hike', 'Recommend Salary Hike'),
        ('bonus', 'Bonus Eligibility'),
        ('promotion', 'Promotion Track'),
        ('low', 'Low Performer'),
    ], string="Outcome Decision", readonly=True)
    outcome_suggestion = fields.Text(string="Outcome Suggestion", readonly=True)


    question_1 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')], readonly=True)
    question_1_justification = fields.Text(string="Your Justification", readonly=True)
    question_1_document = fields.Binary(string="Document", readonly=True)
    question_1_document_filename = fields.Char(string='Filename', readonly=True)

    question_2 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')], readonly=True)
    question_2_justification = fields.Text(string="Your Justification", readonly=True)
    question_2_document = fields.Binary(string="Document", readonly=True)
    question_2_document_filename = fields.Char(string='Filename', readonly=True)

    question_3 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')], readonly=True)
    question_3_justification = fields.Text(string="Your Justification", readonly=True)
    question_3_document = fields.Binary(string="Document", readonly=True)
    question_3_document_filename = fields.Char(string='Filename', readonly=True)

    question_4 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')], readonly=True)
    question_4_justification = fields.Text(string="Your Justification", readonly=True)
    question_4_document = fields.Binary(string="Document", readonly=True)
    question_4_document_filename = fields.Char(string='Filename', readonly=True)

    question_5 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')], readonly=True)
    question_5_justification = fields.Text(string="Your Justification", readonly=True)
    question_5_document = fields.Binary(string="Document", readonly=True)
    question_5_document_filename = fields.Char(string='Filename', readonly=True)

    # @api.constrains('employee_id', 'question_1', 'question_2', 'question_3', 'question_4', 'question_5', 'name')
    # def _check_fields(self):
    #     for record in self:
    #         missing_fields = []
    #         if not record.employee_id:
    #             missing_fields.append('Employee')
    #         if not record.question_1:
    #             missing_fields.append('Question 1')
    #         if not record.question_2:
    #             missing_fields.append('Question 2')
    #         if not record.question_3:
    #             missing_fields.append('Question 3')
    #         if not record.question_4:
    #             missing_fields.append('Question 4')
    #         if not record.question_5:
    #             missing_fields.append('Question 5')
    #         if not record.name or record.name == _('New'):
    #             missing_fields.append('Sequence')

    #         if missing_fields:
    #             raise ValidationError(_('You cannot create a record here. You can only review existing records and update them.'))

    
    def action_done(self):
        for record in self:
            if not record.hr_comment or not record.hr_comment.strip():
                raise ValidationError(_('Please provide HR Comment before marking the feedback as Done.'))
            
            if not record.outcome_decision:
                raise ValidationError(_('Outcome Decision is not added. Please add it before marking the feedback as Done.'))
        
            record.write({'state': 'done'})
            record.state = 'done'

            if record.evaluation_id:
                comm = record.hr_comment
                print("-------------------record.hr_comment-----------------",comm)
                record.evaluation_id.write({
                    'state': 'done',
                    'hr_comment': comm,
                    'outcome_decision': record.outcome_decision,
                    'outcome_suggestion': record.outcome_suggestion
                    })
                record.evaluation_id.state = 'done'

    def check_outcome_decision(self):
        for record in self:
            # Collect internal ratings
            internal_ratings = []
            for i in range(1, 6):
                rating = getattr(record, f'question_{i}')
                if rating is not None:
                    internal_ratings.append(int(rating))
            print("-------------------internal_ratings-----------------",internal_ratings)

            avg_internal = sum(internal_ratings) / len(internal_ratings) if internal_ratings else 0
            print("-------------------avg_internal-----------------",avg_internal)

            # Get 360 feedback ratings for the employee
            feedback360_recs = self.env['hrms.feedback360'].search([
                ('employee_id', '=', record.employee_id.id)
            ])
            external_ratings = []
            for feedback in feedback360_recs:
                if feedback.rating:
                    external_ratings.append(int(feedback.rating))
            print("-------------------external_ratings-----------------",external_ratings)

            avg_external = sum(external_ratings) / len(external_ratings) if external_ratings else 0
            print("-------------------avg_external-----------------",avg_external)

            # Combined weighted average (optional: can tune the weight)
            total_avg = (avg_internal + avg_external) / 2 if external_ratings else avg_internal

            # Decision logic
            if total_avg >= 4.5:
                decision = 'high'
            elif total_avg >= 4.0:
                decision = 'promotion'
            elif total_avg >= 3.5:
                decision = 'bonus'
            elif total_avg >= 3.0:
                decision = 'hike'
            else:
                decision = 'low'

            # Write decision to the record
            # record.outcome_decision = decision

            # Write decision and suggestion
            suggestion = ''
            if decision == 'low':
                suggestion = (
                    "Performance Improvement Plan:\n\n"
                    "1. Responsibilities & Deliverables \n"
                    "- Clearly define and document role expectations with the reporting manager.\n"
                    "- Attend weekly check-in meetings to ensure deliverables are aligned and completed.\n"
                    "- Implement a personal task checklist to track progress daily.\n\n"

                    "2. Task & Project Prioritization \n"
                    "- Undergo training in time management and task prioritization.\n"
                    "- Use project tracking tools to monitor timelines.\n"
                    "- Share a weekly plan with the manager and review pending/blocked tasks.\n\n"

                    "3. Task Timeliness \n"
                    "- Set daily and weekly goals with estimated time of completion.\n"
                    "- Use calendar blocking for deep work and deadlines.\n"
                    "- Review missed deadlines with the supervisor and document reasons with mitigation actions.\n\n"

                    "4. Quality of Service \n"
                    "- Establish a checklist for deliverable quality standards.\n"
                    "- Perform peer reviews before submission of tasks/deliverables.\n"
                    "- Seek feedback from internal or external customers after task completion.\n\n"

                    "5. Problem Solving \n"
                    "- Participate in monthly problem-solving or root cause analysis workshops.\n"
                    "- Maintain a “Problem Resolution Log” documenting the issue, approach, and result.\n"
                    "- Escalate problems promptly and seek collaborative input when needed.\n\n"

                    "Review Timeline:\n"
                    "- Weekly performance review meetings with manager.\n"
                    "- Formal review checkpoints at Week 2 and Week 4.\n\n"

                    "Expected Outcome:\n"
                    "- Demonstrated improvement in all the above areas within 30 to 45 days.\n"
                    "- If insufficient improvement is noted, further action (reassignment, extended PIP, or HR discussion) may follow."
                )

            record.write({
                'outcome_decision': decision,
                'outcome_suggestion': suggestion,
            })

            # Log for debugging
            _logger.info("Final Avg Rating: %s | Decision: %s", total_avg, decision)

    # def test(self):
    #     self.state = 'approved'

