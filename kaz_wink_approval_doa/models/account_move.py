# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Redefine the full selection list to insert coordinator_approval between
    # draft and department_approval, controlling statusbar visual ordering.
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('coordinator_approval', 'Coordinator Approval'),
            ('department_approval', 'Department Approval'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
    )
    delivery_model = fields.Selection(
        selection=[
            ('general', 'General'),
            ('project', 'Project'),
            ('retainer', 'Retainer')
        ],
        string='Delivery Model',
        compute='_compute_delivery_model',
    )
    has_wink_product = fields.Boolean(
        string='Has Wink Product',
        compute='_compute_has_wink_product',
    )

    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id')
    def _compute_delivery_model(self):
        for rec in self:
            wink_products = rec.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.available_on_wink)
            rec.delivery_model = wink_products[0].product_id.delivery_model if wink_products else 'general'

    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id')
    def _compute_has_wink_product(self):
        for rec in self:
            rec.has_wink_product = any(
                line.product_id.available_on_wink for line in rec.invoice_line_ids if
                line.product_id)

    def submit_to_approve(self):
        """Route WINK submissions to Coordinator; delegate KUEC to super()."""
        self.ensure_one()
        if self.company_code == 'WINK':
            self._validate_lines()
            label = self._get_request_label()
            summary = _("%s Request Requires Your Review") % label
            note = _(
                f"The {label} Request has been submitted by {self.env.user.display_name}. "
                f"Please review the {label} Request and proceed with the next steps."
            )
            users = self._get_group_users('kaz_wink_approval_doa.group_wink_coordinator')
            self._perform_action('coordinator_approval', users, summary, note)
            return True
        return super().submit_to_approve()

    def action_coordinator_approval(self):
        """Coordinator approves the document.

        For Vendor Bills (in_invoice) the bill is also posted automatically
        once the approval is confirmed.

        Workflow:
            1. Open signature wizard if not yet signed.
            2. Set kuec_approval_state to 'approved'.
            3. If move_type is 'in_invoice', call action_post() to confirm the bill.
        """
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('approved')
            if self.move_type == 'in_invoice':
                self.action_post()
            return True
        return self._open_approve_reject_wizard('Approve', 'approve', 'action_coordinator_approval')

    def button_draft(self):
        """Reset kuec_approval_state to draft for WINK records on reset-to-draft."""
        res = super().button_draft()
        for rec in self:
            if rec.company_code == 'WINK' and rec.kuec_approval_state != 'draft':
                rec.kuec_approval_state = 'draft'
        return res

    @api.depends_context('uid')
    @api.depends('state')
    def _compute_show_reset_to_draft_button(self):
        """Handle WINK moves first; delegate the rest to super() (which handles KUEC)."""
        wink_moves = self.filtered(lambda m: m.company_code == 'WINK')
        other_moves = self - wink_moves

        user_has_access = self.env.user.has_group(
            'kaz_wink_approval_doa.group_wink_reset_draft'
        )

        for move in wink_moves:
            move.show_reset_to_draft_button = user_has_access and move.state != 'draft'

        if other_moves:
            super(AccountMove, other_moves)._compute_show_reset_to_draft_button()

    def button_cancel(self):
        for order in self:
            if order.company_code in ['WINK']:
                order.kuec_approval_state = 'cancel'
        return super().button_cancel()

    def _validate_lines(self):
        """
        Validates that all invoice lines are consistent with Wink portal
        requirements and shared delivery models.
        """
        super()._validate_lines()

        if self.company_code != 'WINK' or not self.invoice_line_ids:
            return

        # Cache products to avoid multiple database reads
        products = self.invoice_line_ids.mapped('product_id')

        # Check 1: Mandatory Wink Availability
        # If the invoice is flagged as having Wink products, ALL must be compatible.
        if self.has_wink_product:
            incompatible = products.filtered(lambda p: not p.available_on_wink)
            if incompatible:
                raise ValidationError(_(
                    "Portal Compatibility Mismatch: The following products are not "
                    "available on the Wink portal: %s. All items must be Wink-compatible "
                    "when the 'Has Wink Product' flag is active."
                ) % ", ".join(incompatible.mapped('display_name')))

        # Check 2: Uniform Delivery Model
        # We identify all unique delivery models present in the lines.
        unique_models = set(products.mapped('delivery_model'))

        if len(unique_models) > 1:
            # Create a readable list of models found (e.g., 'Project, Retainer')
            model_names = ", ".join(
                dict(self.fields_get(['delivery_model'])['delivery_model']['selection']).get(m, m)
                for m in unique_models if m)

            raise ValidationError(_(
                "Multi-Model Restriction: Invoices for 'WINK' cannot contain mixed delivery models. "
                "The current lines contain a mix of: %s. Please ensure all products "
                "share the same delivery model."
            ) % model_names)

    # @api.constrains('partner_id')
    # def _constrains_partner_id(self):
    #     """
    #     Override to apply parent restrictions ONLY to KUEC/WINK company.
    #     Non-KUEC/WINK records skip this check entirely.
    #     """
    #     applicable_records = self.filtered(lambda rec: rec.company_code in ['KUEC', 'WINK'])
    #     if applicable_records:
    #         super(AccountMove, applicable_records)._constrains_partner_id()
