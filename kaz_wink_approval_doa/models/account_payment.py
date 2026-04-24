# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = ['account.payment', 'approval.base.mixin']
    _name = 'account.payment'

    wink_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string='WINK Approval State',
        default='draft',
        tracking=True,
        copy=False,
    )
    delivery_type = fields.Selection(
        selection=[
            ('general', 'General'),
            ('project', 'Project'),
            ('retainer', 'Retainer'),
        ],
        string='Delivery Type',
        default='general',
    )
    from_bill = fields.Boolean(string='From Bill', default=False, copy=False)
    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    payment_approval_ids = fields.One2many(
        'account.payment.approval', 'payment_id', string='Approval History'
    )
    reconcile_move_line_ids = fields.Many2many(
        'account.move.line',
        'wink_payment_reconcile_rel',
        'payment_id',
        'move_line_id',
        string='Bill Lines to Reconcile',
        copy=False,
    )

    @property
    def _approval_model(self):
        return 'account.payment.approval'

    @property
    def _approval_line(self):
        return self.payment_approval_ids

    @property
    def _approval_state(self):
        return 'wink_approval_state'

    def _approval_context(self):
        self.ensure_one()
        return {'default_payment_id': self.id}

    def _get_request_label(self):
        return _("Payment")

    def submit_to_approve(self):
        """Submit WINK payment for approval based on delivery_type.

        General payments need no approval. Project and retainer payments
        route to the Department Head group.

        Raises:
            UserError: If called on a general-type payment or non-WINK company.
        """
        self.ensure_one()
        if self.company_code != 'WINK':
            return
        if self.delivery_type == 'general':
            raise UserError(_("General payments do not require approval and can be posted directly."))
        summary = _("Payment Request Requires Your Review")
        note = _(
            f"A {self.delivery_type.capitalize()} Payment of {self.amount} {self.currency_id.name} "
            f"has been submitted by {self.env.user.display_name}. "
            f"Please review and proceed with the next steps."
        )
        users = self._get_group_users('kaz_wink_approval_doa.group_wink_head_department')
        self._perform_action('department_approval', users, summary, note)

    def action_hod_approval(self):
        """Department Head approves the payment.

        Workflow:
            1. Open signature wizard if not yet signed.
            2. Check amount against delivery-type threshold.
            3. Route to CCOE if above threshold; otherwise approve and post.
        """
        self.ensure_one()
        if self._context.get('signed', False):
            threshold = 200_000 if self.delivery_type == 'project' else 50_000
            if self.amount > threshold:
                summary = _("Payment Request Requires Your Review")
                note = _(
                    f"A {self.delivery_type.capitalize()} Payment of {self.amount} {self.currency_id.name} "
                    f"has been approved by the Department Head ({self.env.user.display_name}). "
                    f"Amount exceeds the {threshold:,} AED threshold — CCOE approval is required."
                )
                users = self._get_group_users('kaz_wink_approval_doa.group_wink_ccoe')
                self._perform_action('ccoe_approval', users, summary, note)
            else:
                self._approve_and_post()
            return True
        return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_ccoe_approval(self):
        """CCOE approves the payment, completing the workflow."""
        self.ensure_one()
        if self._context.get('signed', False):
            self._approve_and_post()
            return True
        return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_reject_request(self):
        """Reject the payment and notify the creator."""
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Payment Request Rejected")
            note = _(
                f"The Payment Request has been rejected by {self.env.user.display_name}. "
                f"Please review and make the necessary corrections."
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.action_cancel()
            return True
        return self._open_approve_reject_wizard('Reject Payment', 'reject', 'action_reject_request')

    def action_rfc_request(self):
        """Return the payment to draft for correction."""
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Payment Request Returned for Correction")
            note = _(
                f"The Payment Request has been returned for correction by {self.env.user.display_name}. "
                f"Please review and resubmit."
            )
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        return self._open_approve_reject_wizard('Return for Correction', 'rfc', 'action_rfc_request')

    def _approve_and_post(self):
        """Set state to approved, post the payment, and reconcile stored bill lines.

        Workflow:
            1. Set wink_approval_state to 'approved'.
            2. Call action_post() to generate and post the journal entry.
            3. Reconcile payment journal lines against stored bill move lines.
        """
        self.ensure_one()
        self._perform_action('approved')
        self.action_post()
        if self.reconcile_move_line_ids:
            valid_account_types = self._get_valid_payment_account_types()
            domain = [
                ('parent_state', '=', 'posted'),
                ('account_type', 'in', valid_account_types),
                ('reconciled', '=', False),
            ]
            payment_lines = self.move_id.line_ids.filtered_domain(domain)
            bill_lines = self.reconcile_move_line_ids.filtered(lambda l: not l.reconciled)
            if payment_lines and bill_lines:
                (payment_lines + bill_lines).reconcile()
            self.reconcile_move_line_ids = [fields.Command.clear()]

    def action_post(self):
        """Override to block posting for unapproved WINK project/retainer payments."""
        for payment in self:
            if (payment.company_code == 'WINK'
                    and payment.delivery_type in ('project', 'retainer')
                    and payment.wink_approval_state != 'approved'):
                raise UserError(_(
                    "Payment '%s' requires approval before it can be confirmed. "
                    "Please submit it for approval first."
                ) % payment.name)
        return super().action_post()

    def action_cancel(self):
        """Override to update wink_approval_state on cancellation."""
        for payment in self:
            if payment.company_code == 'WINK':
                payment.wink_approval_state = 'cancel'
        return super().action_cancel()
