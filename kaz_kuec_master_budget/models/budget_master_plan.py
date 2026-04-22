from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BudgetMasterPlan(models.Model):
    _name = 'budget.master.plan'
    _description = "Budget Master Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    reference = fields.Char(readonly=True,
                            default='Draft')
    date_start = fields.Date(tracking=True)
    date = fields.Date(tracking=True)
    owner_id = fields.Many2one('res.users',
                               string="Responsible User",
                               default=lambda self: self.env.user.id)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Plan Open'),
        ('close', 'Plan Close'),
        ('active', 'Active'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ],
        default='draft',
        tracking=True,
        copy=False)

    def action_request(self):
        self.write({
            'status': 'open'
        })

    def action_cancel(self):
        self.write({
            'status': 'canceled'
        })

    def action_close(self):
        self.write({
            'status': 'close'
        })

    def action_active(self):
        self.write({
            'status': 'active'
        })

    def action_done(self):
        for budget in self.budget_ids:
            budget.action_budget_done()
        self.write({
            'status': 'done'
        })

    def action_reset(self):
        self.write({
            'status': 'draft'
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code(
                'budget.master.plan')
            vals.update({
                'reference': name
            })
            vals['reference'] = name
        return super().create(vals_list)

    notes = fields.Html()
    created_date = fields.Date(default=fields.Date.today(),
                               readonly=True)
    budget_ids = fields.One2many('budget.analytic',
                                 'master_plan_id')
    company_id = fields.Many2one('res.company',
                                 readonly=True,
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')

    total_reserved_amount = fields.Monetary(
        currency_field='currency_id',
        compute='_calculate_amounts')
    total_committed_amount = fields.Monetary(
        currency_field='currency_id',
        compute='_calculate_amounts')
    total_planned_amount = fields.Monetary(
        currency_field='currency_id',
        compute='_calculate_amounts')
    total_actual_spent = fields.Monetary(
        currency_field='currency_id',
        compute='_calculate_amounts')
    total_remaining = fields.Monetary(
        currency_field='currency_id',
        compute='_calculate_amounts')
    progress = fields.Float(
        compute='_calculate_amounts')

    @api.depends('budget_ids')
    def _calculate_amounts(self):
        for rec in self:
            rec.total_reserved_amount = 0
            rec.total_committed_amount = 0
            rec.total_planned_amount = 0
            rec.total_actual_spent = 0
            rec.total_remaining = 0
            rec.progress = 0
            budgets = rec.budget_ids
            if budgets:
                rec.total_reserved_amount = sum(budgets.mapped(
                    'total_reserved_amount'))
                rec.total_committed_amount = sum(budgets.mapped(
                    'total_committed_amount'))
                rec.total_planned_amount = sum(budgets.mapped(
                    'total_planned_amount'))
                rec.total_actual_spent = sum(budgets.mapped(
                                    'total_practical_amount'))
                rec.total_remaining = rec.total_planned_amount - rec.total_actual_spent
                rec.progress = (rec.total_actual_spent/rec.total_planned_amount) * 100 if rec.total_planned_amount > 0 else 0

    def view_analytic_budgets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": 'budget.analytic',
            "domain": [("id", "in", self.budget_ids.ids)],
            'context': {'create': False,
                        'default_master_plan_id': self.id},
            "name": _("Budgets"),
        }

    def unlink(self):
        for rec in self:
            if rec.status not in ['draft', 'canceled']:
                raise ValidationError(
                    "Cannot delete budget master plan which "
                    "are not in draft or canceled stage."
                )
