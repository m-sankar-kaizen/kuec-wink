from odoo import models, fields


class PartnerChecklistConf(models.Model):
    _inherit = 'partner.checklist.conf'

    for_external_recruiter = fields.Boolean(
        string='For External Recruiter')

