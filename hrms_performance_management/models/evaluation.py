#-*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class Evaluation(models.Model):
    _name = 'hrms.evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Evaluation'

    name = fields.Char(string='Sequence',copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self._default_employee())
    parent_id = fields.Many2one('hr.employee',string="Manager")
    state = fields.Selection([('new','New'),('submitted','Submitted'),('reviewed','Reviewed'),('approved','Approved'),('done','Done')],default="new")
    feedback360_ids = fields.One2many('hrms.feedback360','evaluation_id')
    user_id = fields.Many2one('res.users',default=lambda self: self.env.uid)
    hr_comment = fields.Text(string="HR Comment", readonly=True)
    goal_id = fields.Many2one('my.goals', string="Goal", domain="[('employee_id', '=', employee_id)]")
    outcome_decision = fields.Selection([
        ('high', 'High Performer'),
        ('hike', 'Recommend Salary Hike'),
        ('bonus', 'Bonus Eligibility'),
        ('promotion', 'Promotion Track'),
        ('low', 'Low Performer'),
    ], string="Outcome Decision", readonly=True)
    outcome_suggestion = fields.Text(string="Outcome Suggestion", readonly=True)

    question_1 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')])
    question_1_justification = fields.Text(string="Your Justification")
    question_1_document = fields.Binary(string="Document")
    question_1_document_filename = fields.Char(string='Filename')

    question_2 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')])
    question_2_justification = fields.Text(string="Your Justification")
    question_2_document = fields.Binary(string="Document")
    question_2_document_filename = fields.Char(string='Filename')

    question_3 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')])
    question_3_justification = fields.Text(string="Your Justification")
    question_3_document = fields.Binary(string="Document")
    question_3_document_filename = fields.Char(string='Filename')

    question_4 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')])
    question_4_justification = fields.Text(string="Your Justification")
    question_4_document = fields.Binary(string="Document")
    question_4_document_filename = fields.Char(string='Filename')

    question_5 = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')])
    question_5_justification = fields.Text(string="Your Justification")
    question_5_document = fields.Binary(string="Document")
    question_5_document_filename = fields.Char(string='Filename')

    

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.parent_id = self.employee_id.parent_id.id


    def _default_employee(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee
        else:
            return False
        
    def submit_evaluation(self):
        if not self.goal_id:
            raise ValidationError(_('Please select a Goal before submitting the evaluation. If the your goal is not listed, then you cannot create an evaluation. Once the goal is listed, you can submit the evaluation.'))
    
        self.state = 'submitted'

        # Get employee's email
        employee_email = self.employee_id.work_email or self.employee_id.user_id.email
        print("------------------employee_email--------------------",employee_email)

        # Get performance manager group users
        group = self.env.ref('hrms_performance_management.group_performance_manager')
        group_users = group.users if group else self.env['res.users']
        group_emails = group.users.mapped('email') if group else []
        print("------------------group_emails--------------------",group_emails)

        # Combine and deduplicate emails
        all_emails = list(set(filter(None, [employee_email] + group_emails)))
        print("------------------all_emails--------------------",all_emails)

        # Compose email content
        subject = f"Evaluation Submitted: {self.name}"
        body = f"""
            <p>Hello,</p>
            <p>An evaluation for <strong>{self.employee_id.name}</strong> has been submitted.</p>
            <p>Evaluation ID: <strong>{self.name}</strong></p>
            <p>Please review it in the system.</p>
            <p>Regards,<br/>Odoo HRMS</p>
        """

        # Send email
        for email in all_emails:
            self.env['mail.mail'].create({
                'subject': subject,
                'body_html': body,
                'email_to': email,
                'auto_delete': True,
            }).send()

        # Create activities for group_performance_manager users
        for user in group_users:
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get_id('hrms.evaluation'),
                'res_id': self.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Review Evaluation'),
                'note': _(f'Please review the submitted evaluation {self.name} for {self.employee_id.name}.'),
                'user_id': user.id,
            })


    def approve_evaluation(self):
        for rec in self:
            rec.state = 'approved'

            manager_feedback_exists = any(feedback.feedback_type == 'manager' for feedback in rec.feedback360_ids)
            if not manager_feedback_exists:
                raise ValidationError(_('Manager feedback is required in 360 Feedback before approval. Please create it first.'))
            
            # Create corresponding Performance Feedback record
            feedback_record = self.env['performance.feedback'].create({
                'employee_id': rec.employee_id.id,
                'evaluation_id': rec.id,
                'question_1': rec.question_1,
                'question_1_justification': rec.question_1_justification,
                'question_1_document': rec.question_1_document,
                'question_1_document_filename': rec.question_1_document_filename,
                'question_2': rec.question_2,
                'question_2_justification': rec.question_2_justification,
                'question_2_document': rec.question_2_document,
                'question_2_document_filename': rec.question_2_document_filename,
                'question_3': rec.question_3,
                'question_3_justification': rec.question_3_justification,
                'question_3_document': rec.question_3_document,
                'question_3_document_filename': rec.question_3_document_filename,
                'question_4': rec.question_4,
                'question_4_justification': rec.question_4_justification,
                'question_4_document': rec.question_4_document,
                'question_4_document_filename': rec.question_4_document_filename,
                'question_5': rec.question_5,
                'question_5_justification': rec.question_5_justification,
                'question_5_document': rec.question_5_document,
                'question_5_document_filename': rec.question_5_document_filename,
                'parent_id': rec.parent_id.id,
                'state': 'approved',
                'goal_id': rec.goal_id.id
            })

            # Copy 360 feedback records to Performance Feedback
            feedback_lines = []
            for feedback in rec.feedback360_ids:
                feedback_lines.append((0, 0, {
                    'name': feedback.name,
                    'feedback_provider_id': feedback.feedback_provider_id.id,
                    'feedback_type': feedback.feedback_type,
                    'rating': feedback.rating,
                    'comment': feedback.comment,
                    'suggestion': feedback.suggestion,
                }))
            feedback_record.feedback360_ids = feedback_lines

            # Get group_performance_hr users
            hr_group = self.env.ref('hrms_performance_management.group_performance_hr')
            hr_users = hr_group.users if hr_group else self.env['res.users']
            hr_group_emails = hr_group.users.mapped('email') if hr_group else []

            # Remove empty emails and deduplicate
            hr_group_emails = list(set(filter(None, hr_group_emails)))
            print("------------------hr_group_emails--------------------",hr_group_emails)

            # Compose email content
            subject = f"Evaluation Approved: {self.name}"
            body = f"""
                <p>Hello HR Team,</p>
                <p>The evaluation for <strong>{self.employee_id.name}</strong> has been <strong>approved</strong>.</p>
                <p>Evaluation ID: <strong>{self.name}</strong></p>
                <p>Please proceed with further actions in the system.</p>
                <p>Regards,<br/>Odoo HRMS</p>
            """

            # Send email to HR group users
            for email in hr_group_emails:
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': email,
                    'auto_delete': True,
                }).send()

            # Create activities for HR users
            for user in hr_users:
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('hrms.evaluation'),
                    'res_id': rec.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': _('HR Action Needed'),
                    'note': _(f'The evaluation {self.name} for {rec.employee_id.name} has been approved. Please take necessary action.'),
                    'user_id': user.id,
                })
            

    # def test(self):
    #     self.state = 'new'

    def review_evaluation(self):
        self.state = 'reviewed'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hrms.evaluation') or _('New')
        return super().create(vals_list)
    
    @api.depends('name','employee_id')
    def _compute_display_name(self):
        for rec in self:
            name = rec.name+'-'+rec.employee_id.name
            rec.display_name = name
    