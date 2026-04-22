from odoo import models, fields, api


class AnalyticBudget(models.Model):
    _inherit = 'budget.analytic'

    company_code = fields.Selection(related='company_id.company_code')


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    company_code = fields.Selection(related='company_id.company_code')

    manpower_committed_amount = fields.Float(
        related='staffing_plan_id.total_estimation_per_year',
        store=True
    )
    total_committed_amount = fields.Float(
        compute='_compute_total_committed_amount',
        store=True)

    @api.depends('committed_amount', 'manpower_committed_amount')
    def _compute_total_committed_amount(self):
        for record in self:
            record.total_committed_amount = record.committed_amount + record.manpower_committed_amount

    staffing_plan_id = fields.Many2one('hr.staffing.plan',
                                       compute='_compute_staffing_plan_id',
                                       readonly=False,
                                       inverse='_set_staffing_plan_id')

    def _compute_staffing_plan_id(self):
        for record in self:
            staffing_plan = self.env['hr.staffing.plan'].search([
                ('budget_line_id', '=', record.id)
            ], limit=1)
            record.staffing_plan_id = staffing_plan.id if staffing_plan else False

    def _set_staffing_plan_id(self):
        for record in self:
            if record.staffing_plan_id:
                record.staffing_plan_id.budget_line_id = record.id
            else:
                existing_plan = self.env['hr.staffing.plan'].search([
                    ('budget_line_id', '=', record.id)
                ], limit=1)
                if existing_plan:
                    existing_plan.budget_line_id = False

