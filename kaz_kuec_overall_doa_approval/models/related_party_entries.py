# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RelatedPartyEntries(models.Model):
    _name = 'related.party.entries'
    _inherit = ['related.party.entries', 'approval.base.mixin']

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('ccio_approval', 'CCIO Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('chairman_approval', 'Chairman Approval'),
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
    related_party_approval_ids = fields.One2many('related.party.entries.approval',
                                                 'related_party_id',
                                                 string='Approval/Rejection/Return History')
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment')
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )

    @api.depends('kuec_approval_state', 'kuec_board_attachment')
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment
            )

    @property
    def _approval_model(self):
        return 'related.party.entries.approval'

    @property
    def _approval_line(self):
        return self.related_party_approval_ids

    @property
    def _approval_state(self):
        return 'kuec_approval_state'

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_related_party_id': self.id
        }

    def _get_department_head(self):
        users = self._get_group_users('account.group_account_manager')
        doa_users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_department')
        users += doa_users
        users.filtered(lambda rec: rec.company_id.company_code in ['KUEC'])
        return users.mapped('employee_id')

    def submit_for_approval(self):
        super().submit_for_approval()
        users = self._get_department_head().mapped('user_id')
        summary = _('Approval of Related Party Entries'),
        note = _('Please approve the request for Related Party Entries')
        if self.type in ['cost_allocation', 'investment']:
            self._perform_action('department_approval', users, summary, note)
        else:
            self._perform_common_action('finance_procurement_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Related Party Entries Form Requires Your Review")
        note = _(
            f"The Related Party Entries has been approved by {self.env.user.display_name} "
            "Please review the submitted Related Party Entries form and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def action_hod_approval(self):
        self.ensure_one()
        # self._validate_hod() #TODO validate HOD
        if self._context.get('signed', False):
            if self.type == 'cost_allocation':
                self._perform_common_action('finance_procurement_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            else:
                self._perform_common_action('ccio_approval',
                                            'kaz_kuec_overall_doa_approval.group_cio_kuec')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.type == 'cost_allocation':
                self._perform_action('approved')
                self.action_confirm()
            elif self.type == 'lending':
                self._perform_common_action('ccoe_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ccoe')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_head_fin_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.type == 'lending':
                self._perform_common_action('ceo_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ceo')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ccio_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ceo_approval', 'kaz_procurement_doa_kuec.group_kuec_ceo')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccio_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.type == 'investment':
                if self.amount > 2_000_000:
                    self._perform_common_action('board_approval',
                                                'kaz_procurement_doa_kuec.group_kuec_board')
                else:
                    self._perform_action('approved')
                    self.action_confirm()
            elif self.type == 'lending':
                if self.amount > 3_000_000:
                    self._perform_common_action('chairman_approval',
                                                'kaz_procurement_doa_kuec.group_kuec_chairman')
                else:
                    self._perform_action('approved')
                    self.action_confirm()
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_chairman_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('approved')
            self.action_confirm()
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_chairman_approval')

    def action_board_approval(self):
        self.ensure_one()
        if self.kuec_approval_state == 'board_approval' and not self.kuec_board_attachment:
            raise ValidationError(
                _("Please upload the required Board Approval attachment before proceeding.")
            )
        if self._context.get('signed', False):
            self._perform_action('approved')
            self.action_confirm()
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_board_approval')

    def action_hod_rfc(self):
        self.ensure_one()
        # self._validate_hod()
        return self.action_rfc_request()

    def action_hod_reject(self):
        self.ensure_one()
        # self._validate_hod()
        return self.action_reject_request()

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Related Party Entries Form Rejected")
            note = _(
                f"The Related Party Entries request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Related Party Entries form"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.state = 'canceled'
            return True
        else:
            return self._open_approve_reject_wizard('Reject Related Party Entries', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Related Party Entries Form Returned for Correction")
            note = _(
                f"The Related Party Entries request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Related Party Entries form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            self.state = 'draft'
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')
