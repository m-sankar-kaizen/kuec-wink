# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PettyCashRequest(models.Model):
    _name = 'petty.cash.request'
    _inherit = ['petty.cash.request', 'approval.base.mixin']

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    petty_cash_approval_ids = fields.One2many('petty.cash.request.approval', 'petty_cash_id',
                                              string='Approval/Rejection/Return History')
    settlement_request_ids = fields.One2many('settlement.request', 'petty_cash_id',
                                             string='Settlement Requests')


    @property
    def _approval_model(self):
        return 'petty.cash.request.approval'

    @property
    def _approval_line(self):
        return self.petty_cash_approval_ids

    @property
    def _approval_state(self):
        return 'kuec_approval_state'

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_petty_cash_id': self.id
        }

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Petty Cash Request Requires Your Review")
        note = _(
            f"The Petty Cash Request has been approved by {self.env.user.display_name} "
            "Please review the submitted Petty Cash Request and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def action_submit_request(self):
        res = super().action_submit_request()
        summary = _("Petty Cash Request Requires Your Review")
        note = _(
            f"The Petty Cash Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Petty Cash Request and proceed with the next steps."
        )
        users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
        self._perform_action('finance_procurement_approval', users, summary, note)
        return res

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ccoe_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_ccoe')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ceo_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_ceo')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('approved')
            self.action_approve()
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Petty Cash Request Rejected")
            note = _(
                f"The Petty Cash Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Petty Cash Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.action_reject()
            return True
        else:
            return self._open_approve_reject_wizard('Reject Petty Cash Request', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Petty Cash Request Returned for Correction")
            note = _(
                f"The Petty Cash Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Petty Cash Request"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            self.action_draft()
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_draft(self):
        res = super().action_draft()
        if self.kuec_approval_state != 'draft':
            self._perform_action('draft')
        return res

    def submit_again(self):
        self.ensure_one()
        return self.action_submit_request()

    def action_open_settlements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Requests'),
            'view_mode': 'list,form',
            'res_model': 'settlement.request',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.settlement_request_ids.ids)],
        }

    def submit_for_approval(self):
        self.ensure_one()
        for rec in self.settlement_request_ids:
            if rec.kuec_approval_state == 'draft':
                rec.action_cancel()
            if rec.kuec_approval_state not in ['rejected', 'cancel']:
                raise ValidationError(_(
                    "Please wait until the current approval process is completed before submitting a new request."
                ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Request'),
            'view_mode': 'form',
            'res_model': 'settlement.request',
            'views': [(False, 'form')],
            'context': {
                'default_request_type': 'petty_cash',
                'default_petty_cash_id': self.id,
                'default_settlement_ids': self.settlement_ids.ids,
            }
        }
