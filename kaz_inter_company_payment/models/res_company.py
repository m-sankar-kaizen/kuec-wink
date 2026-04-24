from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    inter_company_payment_ids = fields.One2many(
        'inter.company_payment', 'parent_id')

    def get_intercompany_line(self, company_id):
        return self.inter_company_payment_ids.filtered(
            lambda l: l.company_id.id == company_id)[:1] or False
