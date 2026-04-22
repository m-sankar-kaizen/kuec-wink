# -*- coding: utf-8 -*-
from odoo import fields, models, _


class HrInternshipFeedback(models.Model):
    _name = 'hr.internship.feedback'
    _description = 'Internship Feedback'
    _inherit = ['mail.thread']
    _order = 'feedback_date desc'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, index=True,
                                 help='Company to which this feedback record belongs')

    internship_id = fields.Many2one('hr.internship',
                                    ondelete='cascade', tracking=True,
                                    help='The internship being reviewed')
    
    # Feedback Classification
    feedback_type = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('final', 'Final Evaluation'),
    ], required=True, tracking=True, help='Type of feedback: weekly check-in, monthly review, or final evaluation')

    feedback_date = fields.Date(default=fields.Date.today, required=True,
                               help='Date when feedback was provided')
    
    # Performance Metrics
    performance_score = fields.Selection([
        ('1_poor', 'Needs Improvement'),
        ('2_fair', 'Developing'),
        ('3_good', 'Satisfactory'),
        ('4_very_good', 'Strong Performance'),
        ('5_excellent', 'Outstanding'),
    ], required=True,
        tracking=True,
        help='Performance rating')

    # Feedback Details
    feedback_text = fields.Text(required=True, string='Feedback Comments',
                               help='Comprehensive feedback covering performance, behavior, and technical skills')
    
    # Formal Evaluation Tracking - Per KUEC/POL/003/2025
    is_formal_evaluation = fields.Boolean(default=False, string='Formal Evaluation', tracking=True,
                                         help='Formal mentor evaluation - provides constructive feedback on performance, strengths, and areas for improvement')
    
    goals = fields.Text(string='Goals & Targets',
                       help='Goals and objectives set for the intern')
    achievements = fields.Text(string='Achievements & Accomplishments',
                              help='Accomplishments and successes achieved')
    
    # Mentor Information
    mentor_id = fields.Many2one('hr.employee', required=True, tracking=True,
                               help='Mentor providing the feedback')
    
    # Portal visibility removed per requirements
    
    # Improvement Areas
    improvement_areas = fields.Text(string='Areas for Improvement',
                                   help='Skills or behaviors needing improvement')
    development_plan = fields.Text(string='Development Plan for Next Period',
                                  help='Action plan and recommendations for next period')
    
    # Comments field - internal notes
    comments = fields.Text(default='', string='Internal Comments',
                          help='Internal comments field for tracking purposes')

