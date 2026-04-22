# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrInternshipOrientation(models.Model):
    _name = 'hr.internship.orientation'
    _description = 'Internship Orientation'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, index=True,
                                 help='Company to which this orientation record belongs')

    internship_id = fields.Many2one('hr.internship', required=True, ondelete='cascade', tracking=True,
                                   help='The internship being oriented')
    
    orientation_date = fields.Date(required=True, tracking=True,
                                  help='Scheduled date for orientation session')
    
    # Policy Coverage - Per KUEC/POL/003/2025
    mission_values_covered = fields.Boolean(default=False, string='Mission & Values Covered', tracking=True,
                                           help='Introduction to organization mission and values')
    policies_covered = fields.Boolean(default=False, string='Policies Covered', tracking=True,
                                     help='Workplace policies and procedures explained')
    culture_covered = fields.Boolean(default=False, string='Culture Covered', tracking=True,
                                    help='Workplace culture and expectations introduced')
    code_of_conduct_acknowledged = fields.Boolean(default=False, string='Code of Conduct Acknowledged', tracking=True,
                                                 help='Intern acknowledged KUEC code of conduct')
    
    materials_provided = fields.Text(string='Materials Provided',
                                    help='List of materials provided (handbooks, forms, credentials, guides, etc.)')
    
    # Completion tracking
    is_completed = fields.Boolean(default=False, tracking=True,
                                 help='Check when orientation is completed')
    completion_date = fields.Date(tracking=True, help='Actual completion date of orientation')
    
    # HR Department responsibility
    hr_coordinator_id = fields.Many2one('hr.employee', string='HR Coordinator',
                                        help='HR employee responsible for coordinating orientation')
    
    notes = fields.Text(help='Additional notes about the orientation')
