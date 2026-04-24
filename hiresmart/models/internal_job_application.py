from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import ValidationError, UserError


# [Start] Class for new model "internal job application #######################################################################################################
class InternalJobPost(models.Model):
    _name = 'internal.job.application'
    _description = 'Internal Job Request Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'


# [Start] Fields ###############################################################################################
    job_id = fields.Many2one('hr.job', string='Internal Job Post', required=True, ondelete='cascade')
    recruiter_id = fields.Many2one(related='job_id.user_id', store=True, readonly=True)

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    work_email = fields.Char(related='employee_id.work_email', store=True, readonly=True)
    work_phone = fields.Char(related='employee_id.work_phone', store=True, readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, readonly=True)
    job_position = fields.Many2one(related='employee_id.job_id', store=True, readonly=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', store=True, readonly=True)
    coach_id = fields.Many2one(related='employee_id.coach_id', store=True, readonly=True)
    address_id = fields.Many2one(related='employee_id.address_id', store=True, readonly=True)
    location = fields.Many2one(related='employee_id.work_location_id', store=True, readonly=True)
    working_hours = fields.Many2one(related='employee_id.resource_calendar_id', store=True, readonly=True)
    timezone = fields.Selection(related='employee_id.tz', store=True, readonly=True)
    tag_ids = fields.Many2many(
        'hr.employee.category',
        string='Tags',
        compute='_compute_tag_ids',
        store=True,
        readonly=True,
    )
    ijp_stage = fields.Selection([
            ('new', 'New'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ], default='new', string="Request Status", readonly=True, tracking=True
    )
    rejection_reason_ijp = fields.Text(string='Rejection Reason', tracking=True)
# [End] Fields ###############################################################################################




# [Start] Create function for updating the count of the application at the time for recrod creation ############
    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.mapped('job_id')._compute_new_internal_application_count()
        return res
# [End] Create function for updating the count of the application at the time for recrod creation ############



# [Start] Delete function for updating the count of the application at the time for recrod deletion ############
    def unlink(self):
        jobs = self.mapped('job_id')
        res = super().unlink()
        jobs._compute_new_internal_application_count()
        return res
# [End] Delete function for updating the count of the application at the time for recrod deletion ############



# [Start] Function for changing the record ijp_stage to 'approved' & for creating candidate & applicant record ############################
    def action_internal_job_application_approve(self):
        Applicant = self.env['hr.applicant']
        Candidate = self.env['hr.candidate']

        for rec in self:
            employee = self.env['hr.employee'].browse(rec.employee_id.id)

            partner = self.env['res.partner'].search([
                ('email', '=', rec.work_email)
            ], limit=1)

            candidate = Candidate.create({
                'partner_name': employee.name,
                'partner_id': partner.id,
                'email_from': employee.work_email,
                'partner_phone': employee.work_phone,
                'categ_ids': [(6, 0, employee.category_ids.ids)],
            })

            stage = self.env['hr.recruitment.stage'].search([
                ('name', 'ilike', 'new')
            ], limit=1)

            applicant = Applicant.create({
                'candidate_id': candidate.id,              
                'job_id': rec.job_id.id,
                'user_id': rec.recruiter_id.id,
                'stage_id': stage.id if stage else False,
            })

            rec.ijp_stage = 'approved'

            rec.message_post(
                body=_("✅ Internal Job Application has been <b>approved</b> and a new recruitment applicant has been created."),
                message_type="notification"
            )
# [End] Function for changing the record ijp_stage to 'approved' & for creating candidate & applicant record ############################



# [Start] Function for changing the record ijp_stage to 'rejected' ###########################################################################
    def action_internal_job_application_reject(self):
        for rec in self:
            if not rec.rejection_reason_ijp or not rec.rejection_reason_ijp.strip():
                raise ValidationError("⚠️ Missing Value! \n Please provide a 'rejection reason' before rejecting the hiring request.")
            rec.ijp_stage = 'rejected'
            
            rec.message_post(
                body=Markup(
                    f"Hiring request rejected – <b>Reason:</b> {rec.rejection_reason_ijp.strip()}."
                )
            )
# [End] Function for changing the record ijp_stage to 'rejected' ###########################################################################



# [Start] Function for fetching tag_ids from employee to candidate form #######################################################################
    @api.depends('employee_id')
    def _compute_tag_ids(self):
        for rec in self:
            rec.tag_ids = rec.employee_id.category_ids
# [End] Function for fetching tag_ids from employee to candidate form #######################################################################

# [End] Class for new model "internal job application #########################################################################################################
