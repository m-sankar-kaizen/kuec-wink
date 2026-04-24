from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BudgetAnalytic(models.Model):
    _inherit = 'budget.analytic'

    company_code = fields.Selection(related='company_id.company_code')
    master_plan_id = fields.Many2one(
        'budget.master.plan',
        string="Master Budget",
        domain="[('status', '=', 'open'), ('company_id', '=', company_id)]")

    @api.onchange('master_plan_id')
    def onchange_master_plan_id(self):
        for rec in self:
            rec.date_from = rec.master_plan_id.date_start
            rec.date_to = rec.master_plan_id.date

    def action_budget_confirm(self):
        if self.master_plan_id.status != 'open' and self.company_code == 'KUEC':
            raise ValidationError(
                "Cannot confirm this Budget because"
                " the master plan is not Open."
            )
        return super().action_budget_confirm()

    def action_budget_draft(self):
        if self.master_plan_id.status != 'open' and self.company_code == 'KUEC':
            raise ValidationError(
                "Cannot reset this Budget because"
                " the master plan is not Open."
            )
        return super().action_budget_draft()


class BudgetLines(models.Model):
    _inherit = "budget.line"

    master_plan_id = fields.Many2one(
        'budget.master.plan',
        related='budget_analytic_id.master_plan_id',
        store=True)


