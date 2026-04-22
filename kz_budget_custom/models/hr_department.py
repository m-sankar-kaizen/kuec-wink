from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import time
from odoo.exceptions import UserError
from datetime import datetime


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        required=False)
    budget_id = fields.Many2one(
        comodel_name='budget.analytic', #comodel_name='crossovered.budget',
        string='Budget',
        required=False)

    company_code = fields.Selection(related='company_id.company_code')

    @api.model_create_multi
    def create(self, vals_list):
        plan = self.env.ref('kz_budget_custom.analytic_department')
        for vals in vals_list:
            if vals.get('company_id'):
                company = self.env['res.company'].sudo().browse(vals.get('company_id'))
                if company.company_code != 'KUEC':
                    new_analytic_account = self.env['account.analytic.account'].sudo().create({'name': vals.get('name'), 'plan_id': plan.id})
                    if new_analytic_account:
                        vals['analytic_account_id'] = new_analytic_account.id
        results = super().create(vals_list)
        current_year = datetime.now().year
        first_day_of_year = datetime(current_year, 1, 1)
        last_day_of_year = datetime(current_year, 12, 31)
        for res in results:
            if res.company_code != 'KUEC':
                budget_vals = {
                    'name': res.name or "" + ' Budget',
                    'department_id': res.id,
                    'date_from': first_day_of_year,
                    'date_to': last_day_of_year
                }
                budget = self.env['budget.analytic'].sudo().create(budget_vals)
                res.budget_id = budget.id
        return results

    def view_budget(self):
        view = self.env.ref('account_budget.view_budget_analytic_form')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'budget.analytic',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': self.budget_id.id
        }

