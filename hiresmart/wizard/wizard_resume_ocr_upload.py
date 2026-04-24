from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


# [Start] Class for resume OCR wizard upload ##########################################################################################

class ResumeOCRUploadWizard(models.TransientModel):
    _name = 'resume.ocr.upload.wizard'
    _description = 'Upload Multiple Resumes Wizard'

# [Start] Fields ###########################################################################################
    file_ids = fields.One2many('resume.ocr.upload.line', 'wizard_id', string="Resumes")
    ocr_model = fields.Selection([
        ('mistral', 'Mistral')
    ], string="OCR Model", required=True)
# [End] Fields ###########################################################################################


# [Start] Function for getting OCR related values from rectruitment's setting #############################
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        res.update({'ocr_model': icp.get_param('resume_ocr.ai_provider', 'mistral')})
        return res
# [End] Function for getting OCR related values from rectruitment's setting #############################



# [Start] Function for file passing & calling resume OCR processing #####################################
    def action_upload_ocr(self):
        if not self.file_ids:
            raise UserError("Please add at least one file.")

        config = self.env['ir.config_parameter'].sudo()

        ocr_model = self.ocr_model or config.get_param('resume_ocr.ai_provider')
        if not ocr_model:
            raise UserError("⚠️ OCR Processing Error! \n OCR provider is not configured. Please set it in the recruitment settings under 'OCR [Resume]'.")

        api_key = config.get_param(f'resume_ocr.{ocr_model}_api_key')
        if not api_key:
            raise UserError(f"⚠️ OCR Processing Error! \n API key for OCR provider '{ocr_model}' is missing. Please configure it in recruitment settings under 'OCR [Resume]'.")


        created_records = self.env['resume.ocr']
        for line in self.file_ids:
            # Check for Existing OCR Record ##############################
            existing_ocr = self.env['resume.ocr'].search([
                ('name', '=', line.filename),
                ('file', '=', line.file)
            ], limit=1)

            if existing_ocr:
                _logger.info(f"Duplicate OCR record found: {existing_ocr.name} (ID: {existing_ocr.id})")

                # Prepare updates only for missing values ##################
                updates = {}
                if not existing_ocr.application_id and line.application_id:
                    updates['application_id'] = line.application_id.id
                if not existing_ocr.ocr_model and self.ocr_model:
                    updates['ocr_model'] = self.ocr_model
                if not existing_ocr.ocr_status:
                    updates['ocr_status'] = 'pending'
                if not existing_ocr.ocr_error_message:
                    updates['ocr_error_message'] = ''

                if updates:
                    existing_ocr.write(updates)
                    _logger.info(f"Updated existing OCR record (ID: {existing_ocr.id}) with new info.")
                else:
                    _logger.info("No updates needed for existing OCR record.")

                existing_ocr._process_uploaded_file()
                created_records += existing_ocr

            else:
                # Create New OCR Record ########################
                rec = self.env['resume.ocr'].create({
                    'file': line.file,
                    'name': line.filename,
                    'ocr_model': self.ocr_model,
                    'ocr_status': 'pending',
                })
                rec._process_uploaded_file()
                created_records += rec
        return {}
# [End] Function for file passing & calling resume OCR processing #####################################

# [End] Class for resume OCR wizard upload ##########################################################################################





# [Start] Class for resume OCR wizard upload line ####################################################################################

class ResumeOCRUploadLine(models.TransientModel):
    _name = 'resume.ocr.upload.line'
    _description = 'Resume Upload Line (Multiple)'

# [Start] Fields ##############################################################################
    wizard_id = fields.Many2one('resume.ocr.upload.wizard', string="Wizard")
    file = fields.Binary(string="Resume File", required=True)
    filename = fields.Char(string="File Name")
# [End] Fields ##############################################################################



# [Start] Function for checking duplicate file at the time of uploading #######################
    @api.onchange('file')
    def _onchange_file(self):
        if self.file and not self.filename:
            self.filename = 'UploadedResume_%s.pdf' % fields.Date.today()

        if self.wizard_id and self.filename:
            # Get all lines except this one ######################################
            other_lines = self.wizard_id.file_ids.filtered(lambda l: l != self)
            # Check if any other line has the same filename ######################
            duplicate = any(line.filename == self.filename for line in other_lines)
            if duplicate:
                self.file = False
                self.filename = False
                return {
                    'warning': {
                        'title': "Duplicate File",
                        'message': "The file you're attempting to upload already exists in the upload list.",
                    }
                }
# [End] Function for checking duplicate file at the time of uploading #######################

# [End] Class for resume OCR wizard upload line ####################################################################################
