# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PartnerAttachmentLine(models.Model):
    _inherit = 'partner.attachment.line'

    def _get_target_company_ids(self):
        """
        Helper function to return the list of company IDs to process.
        Modify logic here to fetch from config settings or specific hardcoded IDs.
        """
        # Example 3 (Default): Return all active companies
        return self.env['res.company'].sudo().search([('company_code', 'in', ['KUEC'])]).ids
