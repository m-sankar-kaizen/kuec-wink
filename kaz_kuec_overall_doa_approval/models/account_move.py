# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError, UserError

LABEL_VALUES = {
    'entry': 'Journal Entry',
    'out_invoice': 'Customer Invoice',
    'out_refund': 'Customer Credit Note',
    'in_invoice': 'Vendor Bill',
    'in_refund': 'Vendor Credit Note',
    'out_receipt': 'Sales Receipt',
    'in_receipt': 'Purchase Receipt',
}


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'approval.base.mixin']

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
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
    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    write_off_ids = fields.One2many('write.off.request', 'account_move_id', string='Write Off')
    account_move_approval_ids = fields.One2many('account.move.approval', 'account_move_id',
                                                string='Approval/Rejection/Return History')

    @property
    def _approval_model(self):
        return 'account.move.approval'

    @property
    def _approval_line(self):
        return self.account_move_approval_ids

    @property
    def _approval_state(self):
        return 'kuec_approval_state'

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_account_move_id': self.id
        }

    def action_open_write_off_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Write Off Requests"),
            'view_mode': 'list,form',
            'res_model': 'write.off.request',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.write_off_ids.ids)],
            'context': {
                'create': False,
            }
        }

    def _get_request_label(self):
        return LABEL_VALUES.get(self.move_type, 'Document')

    def _perform_common_action(self, state, group_xml_id):
        label = self._get_request_label()
        summary = _("%s Request Requires Your Review") % label
        note = _(
            f"The {label} Request has been approved by {self.env.user.display_name} "
            f"Please review the submitted {label} Request form and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def _get_department_head(self):
        self.ensure_one()
        employee = self.create_uid.employee_id
        if not employee:
            raise ValidationError(
                _("No Employee found. Please create an employee for this user")
            )
        manager = employee.parent_id
        if not manager:
            raise ValidationError(
                _("No department head found. Please assign a manager to the employee’s department.")
            )
        if not manager.user_id:
            raise ValidationError(
                _("The department head does not have a linked user. Please configure a user for the manager.")
            )
        return manager

    def _validate_hod(self):
        """Validate that the current user is the assigned Department Head.

            Ensures that only the Department Head linked to the employee can
            perform approval actions on the evaluation form.

            Raises:
                UserError: If the current user is not the assigned Department Head.
        """
        self.ensure_one()
        manager = self._get_department_head()
        if manager:
            if manager.user_id:
                if self.env.user != manager.user_id:
                    raise UserError(
                        _("Only the Head of Department assigned to this employee can confirm this request."))
            else:
                raise UserError(_("The Department Head does not have an assigned user."))
        else:
            raise UserError(_("A Department Head is not assigned for this employee."))

    def submit_to_approve(self):
        self.ensure_one()
        if self.company_code not in ['KUEC']:
            return
        # if self.move_type in ['in_invoice']:
        #     source_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')
        #     if not source_orders:
        #         raise ValidationError(_(
        #             "It looks like this Bill isn't linked to a Purchase Order yet. "
        #             "To proceed with approval for KUEC, please link the relevant PO lines first."
        #         ))
        # ### ^^^^^^ Temporarily commented so that they can upload old bills that are already approved.
        label = self._get_request_label()
        summary = _("%s Request Requires Your Review") % label
        note = _(
            f"The {label} Request has been Requested by {self.env.user.display_name} "
            f"Please review the submitted {label} Request and proceed with the next steps."
        )
        # users = self.sudo()._get_group_users('account.group_account_manager').filtered(
        #     lambda rec: rec.sudo().company_id.company_code in ['KUEC'])
        # dep_head = self.sudo()._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_department')
        # users += dep_head
        manager = self._get_department_head()
        self._perform_action('department_approval', manager.user_id, summary, note)

    def action_hod_approval(self):
        self.ensure_one()
        self._validate_hod()
        if self._context.get('signed', False):
            self._perform_common_action('finance_procurement_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.move_type in ['entry', 'out_invoice', 'out_refund', 'out_receipt']:
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
            if self.amount_total > 3_000_000:
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
            self._perform_action('approved')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_reject_request(self):
        self.ensure_one()
        label = self._get_request_label()
        if self._context.get('signed', False):
            summary = _("%s Request Rejected") % label
            note = _(
                f"The {label} Request has been rejected by {self.env.user.display_name}. "
                f"Please review the submitted {label} Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.button_cancel()
            return True
        else:
            return self._open_approve_reject_wizard(f'Reject {label}', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            label = self._get_request_label()
            summary = _("%s Request Returned for Correction") % label
            note = _(
                f"The {label} Request has been Returned for Correction by {self.env.user.display_name}. "
                f"Please review the submitted {label} Request form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            if self.state != 'draft':
                self.button_draft()
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def button_draft(self):
        res = super().button_draft()
        for rec in self:
            if rec.company_code in ['KUEC'] and rec.kuec_approval_state != 'draft':
                rec.kuec_approval_state = 'draft'
        return res

    @api.depends_context('uid')
    @api.depends('state')
    def _compute_show_reset_to_draft_button(self):
        # Separate KUEC moves and non-KUEC moves
        kuec_moves = self.filtered(lambda m: m.company_code in ['KUEC'])
        other_moves = self - kuec_moves

        # Check access for KUEC moves
        user_has_access = self.env.user.has_group(
            'kaz_kuec_overall_doa_approval.group_reset_draft_kuec'
        )

        for move in kuec_moves:
            move.show_reset_to_draft_button = user_has_access and move.state != 'draft'

        # Call super for all non-KUEC moves
        if other_moves:
            super(AccountMove, other_moves)._compute_show_reset_to_draft_button()
