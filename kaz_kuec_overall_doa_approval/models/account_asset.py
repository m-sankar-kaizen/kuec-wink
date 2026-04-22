# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    asset_depreciation_ids = fields.One2many('account.asset.depreciation', 'asset_id',
                                             string='Depreciation Requests')
    asset_investment_type = fields.Selection(
        selection=[
            ('material_part', 'Material Part of Intellectual Property'),
            ('non_investment', 'Non-Investment Assets'),
        ],
        string='Asset Investment Type',
    )

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.asset_investment_type = self.model_id.asset_investment_type

    def _validate_asset_depreciation_ids(self):
        self.ensure_one()
        active_requests = self.asset_depreciation_ids.filtered(
            lambda r: r.kuec_approval_state not in ('rejected', 'cancel')
        )
        if active_requests:
            raise UserError(_(
                "You cannot proceed because there are approved or ongoing "
                "asset depreciation requests for this asset.\n\n"
                "Please reject or cancel the existing request(s) before creating a new one."
            ))

    def action_asset_depreciation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Depreciation Requests'),
            'view_mode': 'list,form',
            'res_model': 'account.asset.depreciation',
            'domain': [('id', 'in', self.asset_depreciation_ids.ids)],
            'views': [(False, 'list'), (False, 'form')],
        }

    def action_asset_modify(self):
        if self.company_code in ['KUEC']:
            self._validate_asset_depreciation_ids()
        return super().action_asset_modify()

    def set_to_cancel(self):
        if self.company_code in ['KUEC']:
            self._validate_asset_depreciation_ids()
        return super().set_to_cancel()
