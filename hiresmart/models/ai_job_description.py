from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json, logging, requests

_logger = logging.getLogger(__name__)


# [Start] [Model: hr.job] Class for adding new field to the hr.job model #######################################

class HrApplicant(models.Model):
    _inherit = 'hr.job'


# [Start] Fields ############################################################################################
    experience = fields.Char(
        string="Experience",
        help="A short free-text description about experience such as '3 years – SaaS marketing'",
    )
# [End] Fields #############################################################################################




# [Start] Function for generating automated job description #################################################
    def action_generate_job_summary(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        ai_provider = IrConfig.get_param('resume_ocr.ai_provider')
        if not ai_provider:
            raise ValidationError(_("⚠️ API Configuration Missing! \n AI provider is not configured. Check Recruitment Settings."))

        api_key = IrConfig.get_param(f'resume_ocr.{ai_provider}_api_key')
        if not api_key:
            raise ValidationError(_(
                "⚠️ API Configuration Missing! \n API key for AI provider '%s' is missing. Configure it in Recruitment Settings.") % ai_provider)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        SYSTEM_MSG = (
            "You are an HR analyst. Based on the following job profile, generate a concise internal job summary (maximum 150 words). "
            "Use only the information explicitly provided. Do not invent, assume, or infer any missing information. "
            "Start the summary by stating that it is an internal job post only if the field 'is_internal_job' is marked true. Otherwise, do not mention it. "
            "You MUST include the job title. If 'experience' is provided, include it; if not, state that the role is open to all (both freshers and experienced candidates). "
            "Only include other fields — such as department, location, industry, employment type, expected skills, and target — if values are actually provided. "
            "Do not start with 'Summary' or any heading. Write the output as a single paragraph in plain text. "
            "Avoid all bullet points, list formatting, or markup symbols. Use a professional and neutral tone."
        )

        for job in self:
            lines = []

            if job.name:
                lines.append(f"Job Title: {job.name}")

            if job.department_id:
                lines.append(f"Department: {job.department_id.name}")

            if job.address_id:
                lines.append(f"Job Location: {job.address_id.display_name}")

            if job.industry_id:
                lines.append(f"Industry: {job.industry_id.name}")

            if job.contract_type_id:
                lines.append(f"Employment Type: {job.contract_type_id.name}")

            if job.experience:
                lines.append(f"Required Experience: {job.experience}")

            if job.no_of_recruitment:
                lines.append(f"Target: {job.no_of_recruitment}")

            if job.skill_ids:
                skills = ", ".join(job.skill_ids.mapped('name'))
                lines.append(f"Expected Skills: {skills}")

            if job.is_internal_job:
                lines.append("Note: This is an internal job post.")

            prompt = "\n".join(lines)

            payload = {
                "model": "pixtral-12b-2409",
                "messages": [
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 130,
                "temperature": 0.2,
            }

            try:
                resp = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers, json=payload, timeout=60
                )
                resp.raise_for_status()
            except (requests.exceptions.RequestException, ValueError) as e:
                raise ValidationError(_("⚠️ Mistral API error:\n%s") % e)

            jd = " ".join(resp.json()['choices'][0]['message']['content'].split())
            job.description = jd
            job.message_post(body="✅ AI-generated job description created.")

        return [
            {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Job Description'),
                    'message': _('✅ AI-generated job description(s) created successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            },
            {'type': 'ir.actions.client', 'tag': 'reload'},
        ]
# [End] Function for generating automated job description #################################################

# [End] [Model: hr.job] Class for adding new field to the hr.job model #########################################