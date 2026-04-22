# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    research_development_id = fields.Many2one('research.development', string='Research Development')

    @api.constrains('research_development_id', 'requisition_type_id')
    def _check_rd_requisition_type(self):
        for rec in self:
            if rec.research_development_id and rec.requisition_type_id:
                if rec.requisition_type_id.requisition_type != 'standard':
                    raise ValidationError(
                        _("The type of requisition for R&D must be 'Standard'.")
                    )

    def submit_to_approve(self):
        if self.research_development_id:
            all_mpr = self.sudo()._read_group(
                domain=[('research_development_id', '=', self.research_development_id.id)],
                groupby=['research_development_id'],
                aggregates=['amount_incurrency:sum'],
            )
            financial_limit = self.company_id.r_and_d_max_financial_limit

            # No financial limit configured
            if not financial_limit:
                raise UserError(_(
                    "Your company has not configured a financial limit for Research & Development requisitions. "
                    "Please set the financial limit under Requisition Settings."
                ))
            total_balance = all_mpr[0]['amount_incurrency'] if all_mpr else 0
            # Amount exceeds the allowed limit
            if total_balance > financial_limit:
                raise UserError(_(
                    "The total requested amount from all the R&D's PR Requests is %s, which exceeds the financial limit of %s allowed for R&D requisitions. "
                    "Please review the financial limit under the Requisition Settings."
                ) % (total_balance, financial_limit))

        return super().submit_to_approve()

    def action_research_development(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('R&D'),
            'res_model': 'research.development',
            'view_mode': 'form',
            'res_id': self.research_development_id.id,
            'views': [(False, 'form')],
        }
