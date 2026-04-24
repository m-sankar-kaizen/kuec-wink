from odoo import models, fields, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    kuec_settlement_conditions = fields.Many2many('kuec.settlement.condition')


class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kuec_settlement_conditions = fields.Many2many(
        'kuec.settlement.condition',
        string='KUEC Settlement Conditions',
        help="Define the settlement conditions for KUEC employees based on years of service.",
        related='company_id.kuec_settlement_conditions',
        readonly=False,
    )


class KuecSettlementCondition(models.Model):
    _name = 'kuec.settlement.condition'
    _description = 'Settlement Condition'

    name = fields.Char(string='Condition', required=True)
    year_start = fields.Integer(string='Year Start',
                                help="Starting year for the condition/ Leave empty for 0")
    year_end = fields.Integer(string='Year End',
                              help="Starting year for the condition/ Leave empty for 0")
    amount = fields.Float(help="Mutiplication of monthly salary",
                          string="Multiplication of Monthly Salary",
                          required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

