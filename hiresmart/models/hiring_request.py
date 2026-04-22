from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import ValidationError, UserError


# [Start] Class for Department head for making hiring request #####################################################################################################

class HiringRequest(models.Model):
    _name = 'hiring.request'
    _description = 'Hiring Request'     
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'requested_by'

# [Start] Fields #########################################################################################################
    user_id = fields.Many2one('res.users', string="User", index=True, default=lambda self: self.env.user)

    # Requester Information #############################################################
    requested_by = fields.Many2one('hr.employee', string='Requested By', required=True, tracking=True)
    department = fields.Many2one('hr.department', string='Department', readonly=True, tracking=True)
    email_address = fields.Char(string='Email Address', readonly=True, tracking=True)
    date_of_request = fields.Date(string='Date of Request', default=fields.Date.today, readonly=True, tracking=True)

    # Position Details ##################################################################
    job_title = fields.Selection([
            ('select_an_option', 'Select an Option'),
            ('developer', 'Developer'),
            ('designer', 'Designer'),
            ('manager', 'Manager'),
            ('analyst', 'Analyst'),
        ], string='Job Title / Position Name', required=True, tracking=True
    )
    number_of_openings = fields.Integer(string='Number of Openings', default=1, tracking=True)
    employment_type = fields.Selection([
            ('select_an_option', 'Select an Option'),
            ('full_time', 'Full-Time'),
            ('part_time', 'Part-Time'),
            ('intern', 'Intern'),
            ('contractual', 'Contractual'),
        ], string='Type of Employment', required=True, tracking=True
    )
    job_level = fields.Selection([
            ('entry', 'Entry Level'),
            ('mid', 'Mid Level'),
            ('senior', 'Senior Level'),
            ('manager', 'Manager/Lead'),
        ], string='Job Level', tracking=True
    )
    work_location = fields.Selection([
            ('on_site', 'On-Site'),
            ('remote', 'Remote'),
            ('hybrid', 'Hybrid'),
        ], string='Work Location', tracking=True
    )

    # Justification/Reason ################################################################
    hiring_reason = fields.Selection([
            ('select_an_option', 'Select an Option'),
            ('replacement', 'Replacement'),
            ('expansion', 'New Role/Expansion'),
            ('project', 'Project Requirement'),
            ('termination', 'Resignation/Termination'),
        ], string='Reason for Hiring', required=True, tracking=True
    )
    justification = fields.Text(string='Explanation / Justification', tracking=True)

    # Job Description & Requirements ######################################################
    job_description = fields.Text(string='Brief Job Description', tracking=True)
    key_skills = fields.Text(string='Key Skill Required', tracking=True)
    min_qualification = fields.Char(string='Minimum Qualification', tracking=True)
    experience_range = fields.Char(string='Preferred Experience Range', tracking=True)
    additional_notes = fields.Text(string='Additional Notes', tracking=True)
    expected_joining_date = fields.Date(string='Expected Joining Date', tracking=True)
    priority = fields.Selection([
            ('select_an_option', 'Select an Option'),
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ], string='Urgency / Priority', required=True, tracking=True
    )

    # Rejection ############################################################################
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)

    # Stage ################################################################################
    stage = fields.Selection([
            ('new', 'New'),
            ('in_process', 'In Process'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ], default='new', string="Request Status", readonly=True, tracking=True
    )
# [End] Fields #########################################################################################################




# [Start] Create function to save the automate populated value of the fields ###########################################
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('requested_by'):
                employee = self.env['hr.employee'].browse(vals['requested_by'])
                vals['department'] = employee.department_id.id
                vals['email_address'] = employee.work_email
                vals['date_of_request'] = fields.Date.today()
        return super(HiringRequest, self).create(vals_list)
# [End] Create function to save the automate populated value of the fields ###########################################



# [Start] Write function to save the automate populated value of the fields ###########################################
    def write(self, vals):
        if 'requested_by' in vals:
            employee = self.env['hr.employee'].browse(vals['requested_by'])
            vals['department'] = employee.department_id.id
            vals['email_address'] = employee.work_email
            vals['date_of_request'] = fields.Date.today()
        return super(HiringRequest, self).write(vals)
# [End] Write function to save the automate populated value of the fields ###########################################



# [Start] Function for populating the other fields onchange of "requested_by" field ########################
    @api.onchange('requested_by')
    def _onchange_requested_by(self):
        for rec in self:
            if rec.requested_by:
                rec.department = rec.requested_by.department_id
                rec.email_address = rec.requested_by.work_email
                rec.date_of_request = fields.Date.today()
# [End] Function for populating the other fields onchange of "requested_by" field ########################



# [Start] Function for changing the record stage to 'in process' ###########################################################################
    def action_in_process(self):
        for rec in self:
            rec.rejection_reason = ''
            rec.stage = 'in_process'
# [End] Function for changing the record stage to 'in process' ###########################################################################



# [Start] Function for changing the record stage to 'approved' ###########################################################################
    def action_approve(self):
        for rec in self:
            rec.stage = 'approved'
# [End] Function for changing the record stage to 'approved' ###########################################################################



# [Start] Function for changing the record stage to 'rejected' ###########################################################################
    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason or not rec.rejection_reason.strip():
                raise ValidationError("⚠️ Missing Value! \n Please provide a 'rejection reason' before rejecting the hiring request.")
            rec.stage = 'rejected'
            
            rec.message_post(
                body=Markup(
                    f"Hiring request rejected – <b>Reason:</b> {rec.rejection_reason.strip()}."
                )
            )
# [End] Function for changing the record stage to 'rejected' ###########################################################################

# [End] Class for Department head for making hiring request #####################################################################################################