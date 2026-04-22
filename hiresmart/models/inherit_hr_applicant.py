from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import json, logging, requests

_logger = logging.getLogger(__name__)


# [Start] Helper function for putting a skill-type label into the right AI bucket ###########################
def _bucket(category_name):
    AI_CATEGORIES = {
        'languages':              ['language', 'languages'],
        'soft_skills':            ['soft skill', 'soft skills'],
        'programming_languages':  ['programming', 'programming language'],
        'marketing_skills':       ['marketing', 'sales', 'advertising'],
        'it_skills':              ['it', 'technology', 'system admin', 'database'],
    }
    cat = (category_name or '').lower()          # handles None ###########
    for bucket, aliases in AI_CATEGORIES.items():
        if cat in aliases:
            return bucket
    return 'other_skills'
# [End] Helper function for putting a skill-type label into the right AI bucket ###########################



# [Start] [Model: hr.applicant] Class for adding new field to the hr.applicant model #######################################

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'


# [Start] Fields ############################################################################################
    is_hiring_request_record = fields.Boolean(
        string="Is Hiring-Request Record",
        default=False,
        help="Internal flag – set to True on records created from a Hiring Request."
    )
    # experience = fields.Char(
    #     string="Experience",
    #     help="A short free-text description about experience such as '3 years – SaaS marketing'",
    # )
    # job_description = fields.Text(string="AI-Generated Job Description",
    #     help="Automate job description creation based on the candidate's skillset and experience provided.",
    # )
    employee_id = fields.Many2one('hr.employee', string="Internal Employee")


    interview_type = fields.Selection([
        ('select', 'Select'),
        ('physical', 'Physical'),
        ('virtual', 'Virtual')
    ], string='Interview Type',default='select', required=True, help="Select the type of interview. If the type is physical, provide the location. If the type is virtual, schedule a meeting by clicking on the button.")

    stage_status = fields.Char(string='Stage Status', store=True, readonly=True, default='New')
# [End] Fields #############################################################################################




# [Start] Write function for sending email to the applicant automatically ################################## 
    # def write(self, vals):
    #     stage_changed = 'stage_id' in vals
    #     res = super().write(vals)
    #     if stage_changed:
    #         for applicant in self:
    #             stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
    #             if stage.name.lower() == 'contract proposal':
    #                 # _logger.info("\n\n EMAIL AUTOMATION DEBUG ----- ")
    #                 # _logger.info("Applicant: %s (ID: %s)", applicant.partner_name, applicant.id)
    #                 # _logger.info("Job Position: %s", applicant.job_id.name)
    #                 # _logger.info("Stage: %s", stage.name)
    #                 # _logger.info("Applicant Email: %s", applicant.email_from)

    #                 config = self.env['recruitment.email.template.config'].search([
    #                     ('job_id', '=', applicant.job_id.id),
    #                     ('is_active', '=', True),
    #                 ], limit=1)

    #                 # _logger.info(f" config ---- {config}")

    #                 if config and config.template_id:
    #                     template = config.template_id
    #                     try:
    #                         _logger.info(" Attempting to send email...")
    #                         mail_id = template.send_mail(applicant.id, force_send=True)
    #                         _logger.info(" Email sent successfully! Mail ID: %s", mail_id)
                            
    #                         if mail_id:
    #                             mail_record = self.env['mail.mail'].browse(mail_id)
    #                             _logger.info(" Email details - State: %s, Recipient: %s", 
    #                                     mail_record.state, mail_record.email_to)
    #                             _logger.info(" Email subject sent: %s", mail_record.subject)
                                
    #                     except Exception as e:
    #                         _logger.error(" Failed to send email: %s", str(e))
    #                         _logger.error("Error type: %s", type(e).__name__)

    #                 else:
    #                     if not config:
    #                         _logger.warning(" No email template config found for job: %s (ID: %s)", 
    #                                 applicant.job_id.name, applicant.job_id.id)
    #                         _logger.info("Available configs: %s", 
    #                                 self.env['recruitment.email.template.config'].search([]).mapped('job_id.name'))
    #                     elif not config.template_id:
    #                         _logger.warning(" Email template config found but no template assigned for job: %s", 
    #                                 applicant.job_id.name)
    #     return res
# [End] Write function for sending email to the applicant automatically #################################### 



# [Start] Function for collecting the skills that are actually present on the skills & experience tab ####### 
    def _collect_skill_data(self):
        # Convert candidate skills into structured dict. ########
        skills_out = {
            "languages": [],
            "programming_languages": [],
            "it_skills": [],
            "marketing_skills": [],
            "soft_skills": [],
            "other_skills": [],
        }

        for line in self.candidate_skill_ids:
            bucket = _bucket(line.skill_type_id.name)
            skills_out[bucket].append({
                "name": line.skill_id.name,
                "level": line.skill_level_id.name or "",
            })
        return skills_out
# [End] Function for collecting the skills that are actually present on the skills & experience tab ####### 

# [End] [Model: hr.applicant] Class for adding new field to the hr.applicant model #######################################
