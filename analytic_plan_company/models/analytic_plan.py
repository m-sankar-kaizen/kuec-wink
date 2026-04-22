from odoo import models, fields


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company.id)


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'

    company_id = fields.Many2one('res.company',
                                 store=True,
                                 related='analytic_plan_id.company_id')


