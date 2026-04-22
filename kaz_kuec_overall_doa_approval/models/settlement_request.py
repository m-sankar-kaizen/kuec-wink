# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SettlementRequest(models.Model):
    _name = 'settlement.request'
    _description = 'Settlement Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'approval.base.mixin']
    _check_company_auto = True
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, default=_('New'))
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    request_type = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('petty_cash', 'Petty Cash'),
    ],
        string='Request Type',
        required=True,
    )
    petty_cash_id = fields.Many2one('petty.cash.request')
    credit_card_id = fields.Many2one('credit.card.request')
    settlement_ids = fields.Many2many('expense.funding.settlement', string='Settlements')

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )

    settlement_request_approval_ids = fields.One2many('settlement.request.approval',
                                                      'settlement_request_id',
                                                      string='Approval/Rejection/Return History')

    def action_open_credit_card(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Card Request'),
            'view_mode': 'form',
            'res_model': 'credit.card.request',
            'views': [(False, 'form')],
            'res_id': self.credit_card_id.id,
        }

    def action_open_petty_cash(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Petty Cash Request'),
            'view_mode': 'form',
            'res_model': 'petty.cash.request',
            'views': [(False, 'form')],
            'res_id': self.petty_cash_id.id,
        }

    def action_cancel(self):
        self.ensure_one()
        if self.kuec_approval_state == 'draft':
            self.kuec_approval_state = 'cancel'

    @property
    def _approval_model(self):
        return 'settlement.request.approval'

    @property
    def _approval_line(self):
        return self.settlement_request_approval_ids

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_settlement_request_id': self.id
        }

    def submit_to_approve(self):
        self.ensure_one()
        summary = _("Settlement Request Requires Your Review")
        note = _(
            f"The Settlement Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Settlement Request and proceed with the next steps."
        )
        users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_department')
        self._perform_action('department_approval', users, summary, note)

    def action_hod_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Settlement Request Requires Your Review")
            note = _(
                f"The Settlement Request has been Requested by {self.env.user.display_name} "
                "Please review the submitted Settlement Request and proceed with the next steps."
            )
            users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_ccoe')
            self._perform_action('ccoe_approval', users, summary, note)

            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_hod_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_ccoe_approval')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Settlement Request Rejected")
            note = _(
                f"The Settlement Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Settlement Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Reject Settlement Request', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Settlement Request Returned for Correction")
            note = _(
                f"The Settlement Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Settlement Request"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_reconcile(self):
        self.ensure_one()
        if self.kuec_approval_state != 'approved':
            raise ValidationError(_(
                "You cannot reconcile this request because it is not fully approved yet."
            ))
        if self.request_type == 'petty_cash':
            return self.petty_cash_id.petty_cash_settlement()
        else:
            return self.credit_card_id.card_cash_settlement()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('settlement.request') or _('New')
        return super().create(vals_list)
