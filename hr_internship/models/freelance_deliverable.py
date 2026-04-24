# -*- coding: utf-8 -*-
from odoo import fields, models


class HrInternshipFreelanceDeliverable(models.Model):
    _name = 'hr.internship.freelance.deliverable'
    _description = 'Freelance Internship Deliverable'
    _order = 'due_date'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, index=True,
                                 help='Company to which this deliverable record belongs')

    internship_id = fields.Many2one('hr.internship', required=True, ondelete='cascade',
                                   help='The freelance internship for this deliverable')
    
    name = fields.Char(required=True, string='Deliverable Name',
                      help='Name or title of the deliverable')
    description = fields.Text(string='Scope of Work',
                             help='Detailed description of deliverable scope and requirements')
    
    due_date = fields.Date(required=True,
                          help='Target due date for completing the deliverable')
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending', help='Current status of the deliverable')
    
    ip_ownership = fields.Text(string='IP Ownership Clauses',
                              help='Intellectual property ownership terms')
    project_terms = fields.Text(string='Project Terms',
                               help='Project terms and conditions')
    
    hours_consumed = fields.Integer(string='Hours Consumed',
                                   help='Number of hours spent on this deliverable')
    
    submission_date = fields.Date(help='Date when deliverable was submitted')
    completion_notes = fields.Text(help='Comments on the completed deliverable')

    def action_start_progress(self):
        """Move deliverable to in progress state"""
        self.state = 'in_progress'

    def action_submit(self):
        """Submit the deliverable"""
        self.state = 'submitted'
        self.submission_date = fields.Date.today()

    def action_accept(self):
        """Accept the submitted deliverable"""
        self.state = 'accepted'

    def action_reject(self):
        """Reject the deliverable and move back to in progress"""
        self.state = 'in_progress'
