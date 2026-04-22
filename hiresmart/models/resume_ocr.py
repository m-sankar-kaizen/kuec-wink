from odoo import models, fields, api
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
from odoo.exceptions import UserError
from io import BytesIO
import imghdr
import magic
import requests
import mimetypes
import base64
import json
import logging
import re

_logger = logging.getLogger(__name__)


# [Start] Class for handling Resume OCR ##################################################################################################################

class OCRResume(models.Model):
    _name = 'resume.ocr'
    _description = 'Resume Upload for OCR Parsing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "application_id"

# [Start] Fields ###########################################################################################################
    name = fields.Char(string="File Name", tracking=True)
    file = fields.Binary(string="Resume File")
    file_type = fields.Selection(
        [
            ('image', 'Image'), 
            ('pdf', 'PDF'), 
            ('other', 'Other')
        ],
        string="File Type", store=True, 
        compute="_compute_file_type"
    )
    page_images_ids = fields.One2many('resume.ocr.page', 'ocr_id', string="PDF Pages")
    pdf_images_html = fields.Html(string="PDF Preview", compute='_compute_pdf_images_html', sanitize=False)
    application_id = fields.Many2one('hr.applicant', string="Created Application For", tracking=True)
    ocr_model = fields.Selection([
        ('mistral', 'Mistral')
    ], string="OCR Model", tracking=True)
    ocr_status = fields.Selection([
        ('new', 'New'), 
        ('pending', 'Pending'), 
        ('done', 'Processed'), 
        ('fail', 'Failed')
    ], string="OCR Status", default='new', tracking=True)
    ocr_error_message = fields.Html(string="OCR Warning")
# [End] Fields ###########################################################################################################



# [Start] Function for changing state to 'new' ###########################################################################
    def _set_status_new(self):
        # _logger.info("\n _set_status_new function called ----- ")
        for rec in self:
            rec.ocr_status = 'new'
# [End] Function for changing state to 'new' ###########################################################################



# [Start] Function for changing state to 'pending' ###########################################################################
    def _set_status_pending(self):
        # _logger.info("\n _set_status_pending function called ----- ")
        for rec in self:
            rec.ocr_status = 'pending'
# [End] Function for changing state to 'pending' ###########################################################################



# [Start] Function for changing state to 'fail' ###########################################################################
    def _set_status_fail(self):
        # _logger.info("\n _set_status_fail function called ----- ")
        for rec in self:
            rec.ocr_status = 'fail'
# [End] Function for changing state to 'fail' ###########################################################################



# [Start] Function for changing state to 'done' ###########################################################################
    def _set_status_done(self):
        # _logger.info("\n _set_status_done function called ----- ")
        for rec in self:
            rec.ocr_status = 'done'
# [End] Function for changing state to 'done' ###########################################################################



# [Start] Trigger create function for (Generating PDF image) ###########################################################
    @api.model_create_multi
    def create(self, vals_list):
        # _logger.info("\n create function called ----- ")
        records = super().create(vals_list)
        for rec in records:
            rec._generate_pdf_images()
        return records
# [End] Trigger create function for (Generating PDF image) ###########################################################



# [Start] Trigger write function for (Regenerating PDF image on file update) ##########################################
    def write(self, vals):
        # _logger.info("\n write function called ----- ")
        res = super().write(vals)
        if 'file' in vals:
            self._generate_pdf_images()
        return res
# [End] Trigger write function for (Regenerating PDF image on file update) ##########################################



# [Start] Function for setting error messages on failure ############################################################
    def _set_error_message(self, message_html):
        """Set a warning message in the ocr_error_message field with HTML content"""
        # _logger.info(f"\n\n message_html ----- {message_html}")
        self.ocr_error_message = ""
        for rec in self:
            rec.ocr_error_message = message_html
# [End] Function for setting error messages on failure ############################################################



# [Start] Fuction for computing uploaded file type ##########################################################
    @api.depends('file')
    def _compute_file_type(self):
        for rec in self:
            rec.file_type = 'other'
            if rec.file:
                try:
                    file_data = base64.b64decode(rec.file)
                    mime = magic.from_buffer(file_data, mime=True)
                    if mime.startswith('image/'):
                        rec.file_type = 'image'
                    elif mime == 'application/pdf':
                        rec.file_type = 'pdf'
                except Exception as e:
                    _logger.error(f"Error in file type detection: {e}")
                    rec.file_type = 'other'
# [End] Fuction for computing uploaded file type ##########################################################



# [Start] Function for generating PDF images ################################################################
    def _generate_pdf_images(self):
        for rec in self:
            # Skip if no file or file is not a PDF ######################
            if not rec.file or rec.file_type != 'pdf':
                continue

            try:
                rec.page_images_ids.unlink()  # Remove existing images ######
                pdf_bytes = base64.b64decode(rec.file)

                # PDF validation ################################
                if not pdf_bytes.startswith(b'%PDF'):
                    raise UserError("Uploaded file is not a valid PDF (missing PDF signature).")

                try:
                    # Lightweight structure validation ##########
                    PdfReader(BytesIO(pdf_bytes))
                except Exception as validation_err:
                    _logger.error(f"Invalid PDF structure: {validation_err}")
                    raise UserError("The uploaded PDF appears to be corrupted or unreadable.")

                # Proceed with conversion #######################
                pages = convert_from_bytes(pdf_bytes)
                for page in pages:
                    buf = BytesIO()
                    page.save(buf, format='PNG')
                    rec.env['resume.ocr.page'].create({
                        'ocr_id': rec.id,
                        'image': base64.b64encode(buf.getvalue()).decode(),
                    })

            except Exception as e:
                _logger.error(f"PDF to image conversion failed: {e}")
                raise UserError("PDF to image conversion failed. Please upload a valid and readable PDF.")
# [End] Function for generating PDF images ###################################################################



# [Start] Function for displaying generated PDF image ##############################################################
    @api.depends('page_images_ids.image')
    def _compute_pdf_images_html(self):
        for rec in self:
            html = ''
            for i, img in enumerate(rec.page_images_ids):
                if img.image:
                    # Safe decode: works for both bytes and str
                    try:
                        image_str = img.image.decode() if isinstance(img.image, bytes) else img.image
                        html += f"""
                            <div style="margin-bottom: 20px;">
                                <div style="font-weight:bold;">Page {i+1}</div>
                                <img src="data:image/png;base64,{image_str}"
                                    alt="PDF Page {i+1}"
                                    style="width:100%; max-width:900px; border:1px solid #ccc; border-radius:4px;" />
                            </div>
                        """
                    except Exception as e:
                        _logger.warning(f"Could not decode image: {e}")
            rec.pdf_images_html = html
# [End] Function for displaying generated PDF image ##############################################################



# [Start] Function for processing uploaded resume file ############################################################
    def _process_uploaded_file(self):
        self.ocr_error_message = ""
        self.page_images_ids = [(5, 0, 0)]
        self._set_status_new()

        if not self.file:
            self.ocr_model = False
            self.application_id = False
            return

        try:
            # Decode + detect MIME ##############################################
            file_bytes = base64.b64decode(self.file)
            mime_type = magic.from_buffer(file_bytes, mime=True)
            # _logger.info(f"\n\n mime_type ----- {mime_type}")
            
            # Check supported types #############################################
            if mime_type not in ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'image/webp']:
                _logger.warning(f"Unsupported MIME type: {mime_type}")
                self._set_status_fail()
                return

            # Generate Preview (PDF to images) ##################################
            if mime_type == 'application/pdf':
                try:
                    pages = convert_from_bytes(file_bytes)
                    vals_list = []
                    for page in pages:
                        img_buffer = BytesIO()
                        page.save(img_buffer, format='PNG')
                        img_data = base64.b64encode(img_buffer.getvalue())
                        vals_list.append((0, 0, {'image': img_data}))
                    self.page_images_ids = vals_list
                    # _logger.info(f"PDF converted to {len(pages)} page images")
                except Exception as e:
                    _logger.error(f"PDF to image conversion failed: {e}")
                    self._set_status_fail()
                    return
            else:
                # For image files, create a single page preview #################
                try:
                    img_data = base64.b64encode(file_bytes)
                    self.page_images_ids = [(0, 0, {'image': img_data})]
                    # _logger.info("Image file loaded for preview")
                except Exception as e:
                    _logger.error(f"Image processing failed: {e}")
                    self._set_status_fail()
                    return

            # Get Configured values #############################################
            config = self.env['ir.config_parameter'].sudo()
            ocr_model = config.get_param('resume_ocr.ai_provider')
            self.ocr_model = ocr_model

            if not ocr_model:
                self._set_status_fail()
                self._set_error_message(f"""
                    <div class="alert alert-danger" role="alert">
                        <strong>OCR Processing Error!</strong><br/>
                        OCR provider is not configured. Please set it in the recruitment settings's under <b>OCR [Resume]</b>.
                    </div>
                """)
                return

            api_key = config.get_param(f'resume_ocr.{ocr_model}_api_key')
            if not api_key:
                # raise UserError(f"API key for {ocr_model} is not configured. Please set it in the recruitment settings's 'OCR [Resume]'.")
                self._set_status_fail()
                self._set_error_message(f"""
                    <div class="alert alert-danger" role="alert">
                        <strong>OCR Processing Error!</strong><br/>
                        API key for <b>{ocr_model}</b> is not configured. Please set it in the recruitment settings under <b>OCR [Resume]</b>.
                    </div>
                """)
                return

            # Call OCR (Mistral Vision API) #####################################
            self._set_status_pending()
            if ocr_model == 'mistral':
                try:
                    # Build a list of image blocks from converted pages ######## 
                    image_blocks = []
                    for page_img in self.page_images_ids:
                        if not page_img.image:
                            continue
                        # decode bytes → str if needed #########################
                        img_str = page_img.image.decode() if isinstance(page_img.image, bytes) else page_img.image
                        image_blocks.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_str}"
                            }
                        })

                    # Build the full message content: prompt + all page images ####
                    message_content = [
                        {
                            "type": "text",
                            "text": """
                                Extract the following information from this resume/CV and return it as JSON:
                                {
                                    "name": "full name",
                                    "email": "email address",
                                    "phone": "phone number",
                                    "linkedin": "linkedin profile URL",
                                    "degree": "Graduate|Bachelor Degree|Master Degree|Doctoral Degree",
                                    "languages": [{"name":"English","level":"C2"},…],
                                    "it_skills": […],
                                    "programming_languages": […],
                                    "soft_skills": […],
                                    "marketing_skills": […],
                                    "other_skills": […],
                                }

                                Instructions:
                                - For degree: Only return one of these exact options…  
                                - For skills: Don’t limit to examples—find *all* relevant skills in each category.  
                                - **Do not duplicate any skill across categories**: if it’s in IT, don’t list it again under Programming Languages, etc.  
                                - **Exclude any hobbies or interests** (e.g. “listening to music,” “visiting new places,” “cooking”) from all skill categories.  
                                - **For every skill in any category, output both its name and its level**;  
                                    • If the CV explicitly mentions a proficiency level, capture it exactly as written, but only if it matches one of the following allowed values:
                                        ["A1", "A2", "B1", "B2", "C1", "C2", "Beginner", "Elementary", "Intermediate", "Upper Intermediate", "Advanced", "Fluent", "Basic"]
                                        **Do not invent or assume any skill level**.
                                    • If the level is not mentioned or does not match one of the allowed values, return the level as an empty string `""` or `null`.
                                - IT skills: technology, software, database, system‐administration skills.  
                                - Programming: languages, frameworks, libraries, development tools.  
                                - Marketing: sales, advertising, social‐media, branding skills.  
                                - Soft skills: leadership, communication, teamwork, problem‐solving skills.  
                                - Other: any remaining professional or technical skills.  
                                - For languages: same rule—leave "level" blank/null when the CV doesn’t mention it.  
                                - If a field isn’t found, return null; if a category has no skills, return an empty array [].
                            """
                        }
                    ] + image_blocks

                    # Assemble the payload #######################################
                    payload = {
                        "model": "pixtral-12b-2409",
                        "messages": [
                            {
                                "role": "user",
                                "content": message_content
                            }
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.1
                    }

                    # Fire the request ############################################ 
                    ocr_response = requests.post(
                        url="https://api.mistral.ai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json=payload,
                        timeout=30
                    )

                    if ocr_response.status_code != 200:
                        _logger.error(f"OCR API Error: {ocr_response.status_code} - {ocr_response.text}")
                        self._set_error_message(f"""
                            <div class="alert alert-danger" role="alert">
                                <strong>OCR Failed!</strong><br/>
                                {ocr_response.text}.
                            </div>
                        """)
                        return

                    result = ocr_response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    # _logger.info(f"OCR Response: {content}")

                    # Try to parse JSON from the response ##########################
                    try:
                        # Extract JSON from response (in case there's extra text) ##
                        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                        if json_match:
                            json_text = json_match.group(1)
                        else:
                            json_text = content
                        extracted = json.loads(json_text)
                            
                    except (json.JSONDecodeError, ValueError) as e:
                        _logger.error(f"Failed to parse OCR response as JSON: {e}")
                        # Fallback: try to extract basic info with regex ############
                        extracted = self._extract_info_fallback(content)

                    # _logger.info(f"OCR Extracted: {extracted}")

                    # Parse fields with null checks #################################
                    name = extracted.get("name") if extracted.get("name") not in [None, "null", ""] else None
                    email = extracted.get("email") if extracted.get("email") not in [None, "null", ""] else None
                    phone = extracted.get("phone") if extracted.get("phone") not in [None, "null", ""] else None
                    linkedin = extracted.get("linkedin") if extracted.get("linkedin") not in [None, "null", ""] else None
                    degree = extracted.get("degree") if extracted.get("degree") not in [None, "null", ""] else None
                    
                    # Extract different skill categories ############################
                    languages = extracted.get("languages", []) if isinstance(extracted.get("languages"), list) else []
                    it_skills = extracted.get("it_skills", []) if isinstance(extracted.get("it_skills"), list) else []
                    programming_languages = extracted.get("programming_languages", []) if isinstance(extracted.get("programming_languages"), list) else []
                    soft_skills = extracted.get("soft_skills", []) if isinstance(extracted.get("soft_skills"), list) else []
                    marketing_skills = extracted.get("marketing_skills", []) if isinstance(extracted.get("marketing_skills"), list) else []
                    other_skills = extracted.get("other_skills", []) if isinstance(extracted.get("other_skills"), list) else []

                    # Create Candidate ##############################################
                    candidate = self.env['hr.candidate'].search([
                        ('partner_name', '=', name),
                        ('email_from', '=', email)
                    ], limit=1)

                    candidate_vals = {
                        'partner_name': name or 'Unknown Candidate',
                        'email_from': email,
                        'partner_phone': phone,
                        'linkedin_profile': linkedin,
                    }

                    if candidate:
                        # _logger.info(f"Candidate already exists: {candidate.partner_name} (ID: {candidate.id})")
                        # Update only missing fields if needed #######################
                        updates = {}
                        if phone and not candidate.partner_phone:
                            updates['partner_phone'] = phone
                        if linkedin and not candidate.linkedin_profile:
                            updates['linkedin_profile'] = linkedin
                        if updates:
                            candidate.write(updates)
                    else:
                        # _logger.info(f"Creating new candidate: {candidate_vals}")
                        candidate = self.env['hr.candidate'].create(candidate_vals)

                    # Attach resume to candidate ####################################
                    existing_candidate_attachment = self.env['ir.attachment'].search([
                        ('res_model', '=', 'hr.candidate'),
                        ('res_id', '=', candidate.id),
                        ('name', '=', self.name)
                    ], limit=1)

                    if not existing_candidate_attachment:
                        self.env['ir.attachment'].create({
                            'name': self.name or 'Resume',
                            'type': 'binary',
                            'res_model': 'hr.candidate',
                            'res_id': candidate.id,
                            'datas': self.file,
                            'mimetype': magic.from_buffer(base64.b64decode(self.file), mime=True),
                            'description': 'Resume attached via OCR',
                        })

                    # Match or Create degree ##########################################
                    degree_mapping = {
                        'Graduate': 'graduate',
                        'Bachelor Degree': 'bachelor', 
                        'Master Degree': 'master',
                        'Doctoral Degree': 'doctoral'
                    }

                    degree_key = False
                    if degree and degree in degree_mapping:
                        mapped_name = degree_mapping[degree]
                        degree_rec = self.env['hr.recruitment.degree'].search([('name', 'ilike', mapped_name)], limit=1)
                        if degree_rec:
                            degree_key = degree_rec.id

                    # Find or Create Applicant #########################################
                    domain = [('candidate_id', '=', candidate.id)]
                    if email:
                        domain.append(('email_from', '=', email))
                    elif phone:
                        domain.append(('partner_phone', '=', phone))

                    application = self.env['hr.applicant'].search(domain, limit=1)

                    application_vals = {
                        'candidate_id': candidate.id,
                        'email_from': email,
                        'partner_phone': phone,
                        'linkedin_profile': linkedin,
                    }

                    if degree_key:
                        application_vals['type_id'] = degree_key

                    new_stage = self.env['hr.recruitment.stage'].search([('name', '=', 'New')], limit=1)
                    if new_stage:
                        application_vals['stage_id'] = new_stage.id

                    if application:
                        application.write({k: v for k, v in application_vals.items() if v and not application[k]})
                    else:
                        application = self.env['hr.applicant'].create(application_vals)

                    self.application_id = application.id
                    
                    existing_applicant_attachment = self.env['ir.attachment'].search([
                        ('res_model', '=', 'hr.applicant'),
                        ('res_id', '=', application.id),
                        ('name', '=', self.name)
                    ], limit=1)

                    if not existing_applicant_attachment:
                        self.env['ir.attachment'].create({
                            'name': self.name or 'Resume',
                            'type': 'binary',
                            'res_model': 'hr.applicant',
                            'res_id': application.id,
                            'datas': self.file,
                            'mimetype': mime_type,
                            'description': 'Resume attached via OCR',
                        })

                    # Get or Create Default Skill Level ##################################
                    default_skill_level_name = 'New Skill (Select Level)'
                    default_skill_level = self.env['hr.skill.level'].search([('name', '=', default_skill_level_name)], limit=1)
                    
                    if not default_skill_level:
                        # _logger.info(f"Creating new skill level: {default_skill_level_name}")
                        default_skill_level = self.env['hr.skill.level'].create({
                            'name': default_skill_level_name,
                            'level_progress': 0
                        })
                    # else:
                        # _logger.info(f"Using existing skill level: {default_skill_level.name}")

                    # Add Candidate Skills by Category ##################################
                    level_mapping = {
                        'A1': 10, 'A2': 20, 'B1': 40, 'B2': 60, 'C1': 80, 'C2': 100,
                        'Beginner': 10, 'Elementary': 20, 'Intermediate': 50, 
                        'Upper Intermediate': 70, 'Advanced': 80, 'Native': 100,
                        'Fluent': 70, 'Basic': 30
                    }

                    skill_categories = {
                        'Languages': languages,
                        'IT': it_skills, 
                        'Programming Languages': programming_languages,
                        'Soft Skills': soft_skills,
                        'Marketing': marketing_skills,
                        'Other': other_skills
                    }
                    
                    for category_name, skills_list in skill_categories.items():
                        # Skip empty categories ########################################
                        if not skills_list or len(skills_list) == 0:
                            # _logger.info(f"Skipping {category_name} - empty")
                            continue
                            
                        # _logger.info(f"Processing {category_name}: {len(skills_list)} skills")
                        
                        # Get or create skill type #####################################
                        skill_type = self.env['hr.skill.type'].search([('name', '=', category_name)], limit=1)
                        if not skill_type:
                            skill_type = self.env['hr.skill.type'].create({'name': category_name})
                        
                        for skill_item in skills_list:
                            if not skill_item:
                                continue
                                
                            # Handle language skills with proficiency levels #########
                            if category_name == 'Languages':
                                skill_name = skill_item.get('name', '').strip()
                                skill_level = (skill_item.get('level') or '').strip() 

                                if not skill_name:
                                    continue

                                try:
                                    if not skill_level:
                                        # No level provided → use default ############
                                        level_rec = default_skill_level
                                        progress = 0
                                    else:
                                        progress = level_mapping.get(skill_level, 50)
                                        level_rec = self.env['hr.skill.level'].search(
                                            [('name', 'ilike', skill_level)], limit=1
                                        )
                                        if not level_rec:
                                            level_rec = self.env['hr.skill.level'].create({
                                                'name': skill_level,
                                                'level_progress': progress
                                            })

                                    # Get or create skill ############################
                                    skill = self.env['hr.skill'].search([
                                        ('name', '=ilike', skill_name),
                                        ('skill_type_id', '=', skill_type.id)
                                    ], limit=1)

                                    if not skill:
                                        skill = self.env['hr.skill'].create({
                                            'name': skill_name,
                                            'skill_type_id': skill_type.id
                                        })
                                    
                                    # Check if skill already exists for candidate ####
                                    existing_skill = self.env['hr.candidate.skill'].search([
                                        ('candidate_id', '=', candidate.id),
                                        ('skill_id', '=', skill.id)
                                    ])
                                    if not existing_skill:
                                        # Final skill values ######################### 
                                        skill_vals = {
                                            'candidate_id': candidate.id,
                                            'skill_id': skill.id,
                                            'skill_level_id': level_rec.id,
                                            'skill_type_id': skill_type.id,
                                            'level_progress': progress,
                                        }
                                        # _logger.info(f"Creating language skill: {skill_name} ({skill_level}) - {progress}%")
                                        self.env['hr.candidate.skill'].create(skill_vals)
                                except Exception as e:
                                    # _logger.error(f"Error creating language skill '{skill_name}': {e}")
                                    continue
                            else:
                                if isinstance(skill_item, dict):
                                    skill_name = (skill_item.get('name')  or '').strip()
                                    level = (skill_item.get('level') or '').strip()
                                else:
                                    skill_name = str(skill_item).strip()
                                    level = ''
                                
                                if not skill_name:
                                    continue
                                    
                                try:
                                    # Get or create skill #########################
                                    skill = self.env['hr.skill'].search([
                                        ('name', '=ilike', skill_name),
                                        ('skill_type_id', '=', skill_type.id)
                                    ], limit=1)
                                    if not skill:
                                        skill = self.env['hr.skill'].create({
                                            'name': skill_name,
                                            'skill_type_id': skill_type.id
                                        })
                                    
                                    # Check if skill already exists for candidate ###
                                    existing_skill = self.env['hr.candidate.skill'].search([
                                        ('candidate_id', '=', candidate.id),
                                        ('skill_id', '=', skill.id)
                                    ])
                                    if not existing_skill:
                                        if not level:
                                            level_rec = default_skill_level
                                            progress = 0
                                        else:
                                            progress = level_mapping.get(level, 50)
                                            level_rec = self.env['hr.skill.level'].search([('name','ilike', level)], limit=1)
                                            if not level_rec:
                                                level_rec = self.env['hr.skill.level'].create({'name': level, 'level_progress': progress})

                                        skill_vals = {
                                            'candidate_id':   candidate.id,
                                            'skill_id':       skill.id,
                                            'skill_level_id': level_rec.id,
                                            'skill_type_id':  skill_type.id,
                                            'level_progress': progress,
                                        }
                                        # _logger.info(f"Creating skill: {skill_name} with 0% progress")
                                        self.env['hr.candidate.skill'].create(skill_vals)
                                except Exception as e:
                                    # _logger.error(f"Error creating skill '{skill_name}': {e}")
                                    continue

                    # Set record state to 'Done' ###################################
                    self._set_status_done()
                    self.write({
                        'application_id': application.id,
                        'ocr_model': ocr_model,
                        'ocr_status': 'done'
                    })
                    # _logger.info(f"OCR processing completed successfully for candidate: {name}")

                except Exception as e:
                    _logger.error(f"OCR processing failed: {e}")
                    self._set_status_fail()
                    self._set_error_message(f"""
                        <div class="alert alert-danger" role="alert">
                            <strong>OCR Processing Failed!</strong><br/>
                            {str(e)}.
                        </div>
                    """)
                    return

        except Exception as e:
            _logger.error(f"General error during OCR handling: {e}")
            self._set_status_fail()
            self._set_error_message(f"""
                <div class="alert alert-danger" role="alert">
                    <strong>File Processing Failed!</strong><br/>
                    {str(e)}.
                </div>
            """)
            return
# [End] Function for processing uploaded resume file ############################################################



# [Start] Fallback function for extracting basic info using regex when JSON parsing fails #######################
    def _extract_info_fallback(self, content):
        extracted = {}
        
        # Extracting email ########################################
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
        if email_match:
            extracted['email'] = email_match.group()
        
        # Extracting phone (basic patterns) #######################
        phone_match = re.search(r'[\+]?[1-9]?[\d\s\-\(\)]{8,15}', content)
        if phone_match:
            extracted['phone'] = phone_match.group().strip()
        
        # Extracting LinkedIn URL #################################
        linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', content, re.IGNORECASE)
        if linkedin_match:
            extracted['linkedin'] = f"https://{linkedin_match.group()}"
        
        return extracted
# [End] Fallback function for extracting basic info using regex when JSON parsing fails #######################



# [Start] Function for calling OCR processing for a given candidate when file is uploaded ########################
    @api.onchange('file')
    def _onchange_file(self):
        if self.file:
            # Check for duplicate resumes based on binary content
            duplicate = self.env['resume.ocr'].search([
                ('file', '=', self.file),
                ('id', '!=', self.id)
            ], limit=1)

            if duplicate:
                raise UserError("⚠️ OCR Processing Error! \n This file already exists in the system. Please upload a different resume.")
            
            self._process_uploaded_file()
# [End] Function for calling OCR processing for a given candidate when file is uploaded ########################



# [Start] Function for changing record state on-change of 'application_id' #####################################
    @api.onchange('application_id')
    def _onchange_application_id_set_new_stage(self):
        # _logger.info("\n Function called _onchange_application_id_set_new_stage ----- ")
        if not self.application_id:
            self._set_status_new()
        elif self.application_id:
            self._set_status_done()
# [End] Function for changing record state on-change of 'application_id' #####################################



# [Start] (Form view) Function for calling resume OCR processing when clicked on rerun OCR button #############
    def action_rerun_ocr(self):
        for rec in self:
            rec._process_uploaded_file()
# [End] (Form view) Function for calling resume OCR processing when clicked on rerun OCR button ###############



# [Start] (List view) Function for calling resume OCR batch processing when clicked on rerun OCR button #######
    def action_resume_ocr_batch_rerun(self):
        # _logger.info("Function called: action_resume_ocr_batch_rerun -----")

        config = self.env['ir.config_parameter'].sudo()
        skipped_records = 0
        processed_records = 0

        ocr_model = self.mapped('ocr_model') or [config.get_param('resume_ocr.ai_provider')]
        ocr_model = ocr_model[0] if ocr_model else False

        if not ocr_model:
            raise UserError("⚠️ OCR Processing Error! \n AI provider is not configured. Please set it in Recruitment Settings.")

        api_key = config.get_param(f'resume_ocr.{ocr_model}_api_key')
        if not api_key:
            raise UserError(f"⚠️ OCR Processing Error! \n API key for AI provider '{ocr_model}' is missing. Please configure it in Recruitment Settings.")

        for rec in self:
            if rec.ocr_status in ['new', 'done', 'fail']:
                try:
                    if not rec.ocr_model:
                        rec.ocr_model = ocr_model

                    rec._process_uploaded_file()
                    processed_records += 1
                except Exception as e:
                    _logger.error(f"OCR failed for record {rec.id}: {e}")
            else:
                skipped_records += 1

        message = f"OCR re-run completed.\nProcessed: {processed_records}, Skipped: {skipped_records}"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "OCR Re-run Result",
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
# [End] (List view) Function for calling resume OCR batch processing when clicked on rerun OCR button #######

# [End] Class for handling Resume OCR ##################################################################################################################





# [Start] Class for handling uploaded resume files #####################################################################################################

class ResumeOCRPage(models.Model):
    _name = 'resume.ocr.page'
    _description = 'PDF Page Image for OCR Resume'

# [Start] Fields ###################################################################################################
    image = fields.Text(string="Page Image (Base64 String)")
    ocr_id = fields.Many2one('resume.ocr', string="Resume")
# [End] Fields #####################################################################################################

# [End] Class for handling uploaded resume files #####################################################################################################
