# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError


class AccountAssetDepreciation(models.Model):
    _name = 'account.asset.depreciation'
    _description = 'Asset Modification Request'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin', 'approval.base.mixin']

    name = fields.Char(string='Name', required=True, default=_('New'))
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    modify_action = fields.Selection(
        selection=[
            ('dispose', 'Dispose'),
            ('sell', 'Sell'),
            ('modify', 'Re-evaluate'),
            ('pause', 'Pause'),
        ],
        default='dispose',
        string='Action',

    )
    date = fields.Date(string='Date')
    loss_account_id = fields.Many2one('account.account', string='Loss',
                                      domain="[('deprecated', '=', False)]")
    note = fields.Text(string='Note')
    asset_id = fields.Many2one('account.asset', string='Asset')
    asset_investment_type = fields.Selection(related='asset_id.asset_investment_type')
    original_value = fields.Monetary(related='asset_id.original_value',
                                     currency_field='currency_id')
    invoice_ids = fields.Many2many('account.move', string='Invoices')
    invoice_line_ids = fields.Many2many('account.move.line', string='Invoice Lines')
    method_number = fields.Integer(string='Duration', required=True)
    method_period = fields.Selection([('1', 'Months'), ('12', 'Years')],
                                     string='Number of Months in a Period',
                                     help="The amount of time between two depreciations")
    value_residual = fields.Monetary(string="Depreciable Amount",
                                     help="New residual amount for the asset",
                                     compute="_compute_value_residual", store=True, readonly=False)
    salvage_value = fields.Monetary(string="Not Depreciable Amount",
                                    help="New salvage amount for the asset")
    currency_id = fields.Many2one(related='asset_id.currency_id')
    account_asset_id = fields.Many2one(
        'account.account',
        string="Gross Increase Account",
        check_company=True,
        domain="[('deprecated', '=', False)]",
    )
    account_depreciation_id = fields.Many2one(
        'account.account',
        check_company=True,
        domain="[('deprecated', '=', False)]",
        string="Depreciation Account",
    )
    account_depreciation_expense_id = fields.Many2one(
        'account.account',
        check_company=True,
        domain="[('deprecated', '=', False)]",
        string="Expense Account",
    )
    is_readonly = fields.Boolean(string='Is Readonly')
    gain_or_loss = fields.Selection([('gain', 'Gain'), ('loss', 'Loss'), ('no', 'No')],
                                    string='Gain/Loss')
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('board_approval', 'KUEC Board Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment')
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )
    depreciation_approval_ids = fields.One2many('account.asset.depreciation.approval',
                                                'depreciation_id',
                                                string='Approval/Rejection/Return History')

    def copy(self, default=None):
        raise UserError(_("You cannot duplicate an Asset Depreciation request."))

    @property
    def _approval_model(self):
        return 'account.asset.depreciation.approval'

    @property
    def _approval_line(self):
        return self.depreciation_approval_ids

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_depreciation_id': self.id
        }

    @api.depends('kuec_approval_state', 'kuec_board_attachment')
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment
            )

    def unlink(self):
        if not self._context('force_delete', False):
            raise UserError(_("You cannot delete an Asset Depreciation request."))
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('account.asset.depreciation') or _(
                'New')
        return super().create(vals_list)

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Asset Modification Request Request Requires Your Review")
        note = _(
            f"The Asset Modification Request Request has been approved by {self.env.user.display_name} "
            "Please review the submitted Asset Modification Request Request and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def submit_to_approve(self):
        self.ensure_one()
        summary = _("Asset Modification Request Request Requires Your Review")
        note = _(
            f"The Asset Modification Request Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Asset Modification Request Request and proceed with the next steps."
        )
        users = self.sudo()._get_group_users('account.group_account_manager').filtered(
            lambda rec: rec.sudo().company_id.company_code in ['KUEC'])
        dep_head = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_department')
        users += dep_head
        self._perform_action('department_approval', users, summary, note)

    def action_hod_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('finance_procurement_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.modify_action in ['modify', 'pause']:
                self._perform_action('approved')
            else:
                self._perform_common_action('ccoe_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_ccoe')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.asset_investment_type == 'material_part' or (
                    self.asset_investment_type == 'non_investment' and self.original_value > 50_000):
                self._perform_common_action('ceo_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ceo')
            else:
                self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.asset_investment_type == 'material_part':
                self._perform_common_action('board_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_board')
            else:
                self._perform_action('approved')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_board_approval(self):
        self.ensure_one()
        if self.kuec_approval_state == 'board_approval' and not self.kuec_board_attachment:
            raise ValidationError(
                _("Please upload the required Board Approval attachment before proceeding.")
            )
        if self._context.get('signed', False):
            self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_board_approval')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Asset Modification Request Request Rejected")
            note = _(
                f"The Asset Modification Request Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Asset Modification Request Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Reject Asset Depreciation Request', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Asset Modification Request Request Returned for Correction")
            note = _(
                f"The Asset Modification Request Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Asset Modification Request Request"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_cancel(self):
        self.ensure_one()
        self.kuec_approval_state = 'cancel'

    def action_asset_modify(self):
        self.ensure_one()
        if self.kuec_approval_state != 'approved':
            raise UserError(_(
                "You can create an asset modification only after this request is fully approved."
            ))
        new_wizard = self.env['asset.modify'].create({
            'company_id': self.company_id.id,
            'modify_action': self.modify_action,
            'date': self.date,
            'name': self.note,
            'loss_account_id': self.loss_account_id.id,
            'asset_id': self.asset_id.id,
            'invoice_ids': self.invoice_ids.ids,
            'invoice_line_ids': self.invoice_line_ids.ids,
            'method_number': self.method_number,
            'method_period': self.method_period,
            'value_residual': self.value_residual,
            'salvage_value': self.salvage_value,
            'account_asset_id': self.account_asset_id.id,
            'account_depreciation_id': self.account_depreciation_id.id,
            'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
            'is_readonly': True,
            'is_approved': True,
            'gain_or_loss': self.gain_or_loss,
        })
        return {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'asset.modify',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }
