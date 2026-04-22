from odoo import models, fields, api,_
from odoo.exceptions import UserError


# [Start] [Model: hr.job & hr.applicant] Class for adding new field & button for internal job posting #######################################

class HrJob(models.Model):
    _inherit = 'hr.job'


# [Start] Fields ####################################################################################################
    is_internal_job = fields.Boolean(string='Is Internal Job Post?')
    application_count = fields.Integer("Total Applications", compute="_compute_application_count", store=True)
    new_internal_application_count = fields.Integer(
        string="New Internal Applications",
        compute="_compute_new_internal_application_count",
        store=True
    )
# [End] Fields #######################################################################################################




# [Start] Function for opening job applicant form for internal job post ##############################################
    def action_create_internal_application(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply for Internal Job',
            'res_model': 'internal.job.application',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_job_id': self.id,
            }
        }
# [End] Function for opening job applicant form for internal job post #################################################



# [Start] Function to calculating total no. of final new application for internal job post ####################################
    @api.depends('application_ids')
    def _compute_application_count(self):
        for job in self:
            job.application_count = len(job.application_ids)
# [End] Function to calculating total no. of final new application for internal job post ####################################



# [Start] Function for calculating total no. of internal job post request application ###############################
    def _compute_new_internal_application_count(self):
        for job in self:
            job.new_internal_application_count = self.env['internal.job.application'].search_count([
                ('job_id', '=', job.id)
            ])
# [End] Function for calculating total no. of internal job post request application ###############################

# [End] [Model: hr.job & hr.applicant] Class for adding new field & button for internal job posting #######################################
