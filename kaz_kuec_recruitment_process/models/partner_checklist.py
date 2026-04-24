from odoo import models, fields


class PartnerChecklist(models.Model):
    _inherit = 'partner.checklist'

    for_external_recruiter = fields.Boolean(
        'For External Recruiter')
