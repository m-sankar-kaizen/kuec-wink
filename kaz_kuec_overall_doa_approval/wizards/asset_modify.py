# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    is_readonly = fields.Boolean(string='Is Readonly')
    is_approved = fields.Boolean(string='Is Approved')

    def action_submit_for_approval(self):
        self.ensure_one()
        self.asset_id._validate_asset_depreciation_ids()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Depreciation Request'),
            'view_mode': 'form',
            'res_model': 'account.asset.depreciation',
            'views': [(False, 'form')],
            'context': {
                'default_company_id': self.company_id.id,
                'default_modify_action': self.modify_action,
                'default_date': self.date,
                'default_note': self.name,
                'default_loss_account_id': self.loss_account_id.id,
                'default_asset_id': self.asset_id.id,
                'default_invoice_ids': self.invoice_ids.ids,
                'default_invoice_line_ids': self.invoice_line_ids.ids,
                'default_method_number': self.method_number,
                'default_method_period': self.method_period,
                'default_value_residual': self.value_residual,
                'default_salvage_value': self.salvage_value,
                'default_account_asset_id': self.account_asset_id.id,
                'default_account_depreciation_id': self.account_depreciation_id.id,
                'default_account_depreciation_expense_id': self.account_depreciation_expense_id.id,
                'default_is_readonly': True,
                'default_gain_or_loss': self.gain_or_loss,
            },
        }
