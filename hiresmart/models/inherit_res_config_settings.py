from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

# [Start] Fields ###########################################################################################################
    ai_provider = fields.Selection([
        ('mistral', 'Mistral AI'),
    ], string="OCR Provider", default='mistral')
    selected_api_key = fields.Char(string="API Key")
# [End] Fields ###########################################################################################################



# [Start] Function for getting the value of ai_provider & its API key ####################################################
    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        provider = icp.get_param('resume_ocr.ai_provider', default='mistral')
        res.update(
            ai_provider=provider,
            selected_api_key=icp.get_param(f'resume_ocr.{provider}_api_key', default='')
        )
        return res
# [End] Function for getting the value of ai_provider & its API key ######################################################



# [Start] Function for setting the value of ai_provider & its API key ####################################################
    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('resume_ocr.ai_provider', self.ai_provider or 'mistral')
        if self.ai_provider:
            icp.set_param(f'resume_ocr.{self.ai_provider}_api_key', self.selected_api_key or '')
# [End] Function for setting the value of ai_provider & its API key ######################################################
