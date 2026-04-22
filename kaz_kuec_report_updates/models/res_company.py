from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    kuec_bank_id = fields.Many2one('res.bank', string='Bank Name')
    iban_num = fields.Char(string='IBAN Number')
    branch_name = fields.Char()
    kuec_account_no = fields.Char(string='Account Number')
    beneficiary = fields.Char(string='Beneficiary Name')
    swift_code = fields.Char(string='SWIFT Code')


