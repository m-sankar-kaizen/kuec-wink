from odoo import models, fields, api, _


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    progress = fields.Float(string="Progress",
                            compute='compute_progress',
                            help="(Actual Spent Amount / Planned Budget) × 100")

    ref = fields.Char(string='REF',
                      default="New")
    budget_short_code = fields.Char(
        related='budget_analytic_id.short_code',
        store=True)

    budget_line_tag_id = fields.Many2one(
        'account.account.tag',
        related='general_budget_id.budgetary_position_tag_id',
        store=True)

    @api.depends('general_budget_id',
                 'general_budget_id.account_ids',
                 'general_budget_id.account_ids.tag_ids')
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to assign a sequence to the name field
        if it is not explicitly provided.
        """
        for vals in vals_list:
            if not vals.get('ref') or vals['ref'] == _('New'):
                short_code = ''
                if vals.get('budget_analytic_id'):
                    short_code = self.env[
                        'budget.analytic'].sudo().browse(
                        vals.get('budget_analytic_id')).short_code
                seq = self.env['ir.sequence'].next_by_code('budget.line.seq') or _('New')
                seq = seq.replace('xx', short_code)
                vals['ref'] = seq
        return super().create(vals_list)

    @api.onchange('achieved_amount', 'masked_planned_amount')
    def compute_progress(self):
        for rec in self:
            rec.progress = rec.achieved_amount/rec.masked_planned_amount if rec.masked_planned_amount != 0 else 0.0
