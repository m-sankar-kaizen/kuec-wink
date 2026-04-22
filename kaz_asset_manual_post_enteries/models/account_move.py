# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import (
    float_compare, formatLang, format_date, get_lang
)


class AccountMove(models.Model):
    """
        Inherits `account.move` to customize the
         posting behavior of invoices and journal entries.

        Key Customizations:
        -------------------
        - Adds validation checks for invoice totals,
         bank accounts, and partner fields.
        - Introduces logic to prevent posting if
        certain asset-related conditions exist.
        - Overrides `_post()` and `action_post()` methods
        to inject business-specific posting behavior:
            * Asset-related moves are held in draft
             until explicitly validated.
            * Zero-amount invoices are automatically
            marked as paid.
            * Recurring invoice hooks, analytic lines,
             and depreciation logic are retained from base behavior.

        Additional Notes:
        -----------------
        This module is particularly designed for
         environments with asset management workflows
        that require controlled posting behavior
         (e.g., for draft-stage asset-related moves).
        """
    _inherit = 'account.move'

    def _post(self, soft=True):
        """
        Custom override of Odoo's `_post` method to
         perform additional validations and
        asset-specific logic before actually posting the move.

        Args:
            soft (bool): If True, moves with future
             dates are not posted immediately but scheduled.
        Returns:
            recordset: Posted account.move records.
        """

        # Access control: ensure user has rights to post invoices
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))

        for invoice in self.filtered(lambda m: m.is_invoice(include_receipts=True)):
            # Validation: Quick edit mode total mismatch
            if (
                invoice.quick_edit_mode and
                invoice.quick_edit_total_amount and
                invoice.currency_id.compare_amounts(invoice.quick_edit_total_amount, invoice.amount_total) != 0
            ):
                raise UserError(_(
                    "The current total is %s but the expected total is %s. Adjust invoice lines or expected total.",
                    formatLang(self.env, invoice.amount_total, currency_obj=invoice.currency_id),
                    formatLang(self.env, invoice.quick_edit_total_amount, currency_obj=invoice.currency_id),
                ))

            # Validation: Archived bank account
            if invoice.partner_bank_id and not invoice.partner_bank_id.active:
                raise UserError(_("The recipient bank account linked to this invoice is archived."))

            # Validation: Negative invoice amount not allowed
            if float_compare(invoice.amount_total, 0.0, precision_rounding=invoice.currency_id.rounding) < 0:
                raise UserError(_(
                    "You cannot validate an invoice with a negative total. Use a credit note instead."
                ))

            # Validation: Ensure partner is set
            if not invoice.partner_id:
                if invoice.is_sale_document():
                    raise UserError(_("The field 'Customer' is required."))
                elif invoice.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required."))

            # Default invoice date handling
            if not invoice.invoice_date:
                if invoice.is_sale_document(include_receipts=True):
                    invoice.invoice_date = fields.Date.context_today(self)
                elif invoice.is_purchase_document(include_receipts=True):
                    raise UserError(_("The Bill/Refund date is required to validate this document."))

        for move in self:
            # Prevent double posting
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))

            # Ensure there is at least one line (excluding notes/sections)
            if not move.line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
                raise UserError(_('You need to add a line before posting.'))

            # Prevent soft posting of future-dated entries unless configured
            if not soft and move.auto_post != 'no' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))

            # Prevent using archived journals
            if not move.journal_id.active:
                raise UserError(_(
                    "You cannot post an entry in an archived journal (%(journal)s)",
                    journal=move.journal_id.display_name,
                ))

            # Prevent posting with inactive currency
            if move.display_inactive_currency_warning:
                raise UserError(_("You cannot validate a document with an inactive currency: %s", move.currency_id.name))

            # Prevent posting with deprecated accounts
            if move.line_ids.account_id.filtered(lambda acc: acc.deprecated):
                raise UserError(_("A line of this move is using a deprecated account, you cannot post it."))

        # Handle future-dated moves separately if soft=True
        if soft:
            future_moves = self.filtered(lambda m: m.date > fields.Date.context_today(self))
            for move in future_moves:
                if move.auto_post == 'no':
                    move.auto_post = 'at_date'
                msg = _('This move will be posted at the accounting date: %(date)s',
                        date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        # Adjust move dates if lock dates are violated
        for move in to_post:
            if move._get_violated_lock_dates(move.date, move._affect_tax_report()):
                move.date = move._get_accounting_date(move.invoice_date or move.date, move._affect_tax_report())

        # Batch create analytic lines
        to_post.line_ids._create_analytic_lines()

        # Handle recurring invoice logic
        to_post.filtered(lambda m: m.auto_post not in ('no', 'at_date'))._copy_recurring_entries()

        # Ensure invoice line partner consistency
        for invoice in to_post:
            wrong_lines = invoice.is_invoice() and invoice.line_ids.filtered(
                lambda l: l.partner_id != invoice.commercial_partner_id and l.display_type not in ('line_note', 'line_section'))
            if wrong_lines:
                wrong_lines.write({'partner_id': invoice.commercial_partner_id.id})

        # Custom behavior for asset-related invoices
        if to_post.asset_id and not self.env.context.get('called_from_validation'):
            # Instead of posting, revert to draft and flag as posted_before
            to_post.write({
                'state': 'draft',
                'posted_before': True,
            })
        else:
            # Proceed with posting
            to_post.write({
                'state': 'posted',
                'posted_before': True,
            })

        # Auto subscribe partner if missing
        for invoice in to_post:
            invoice.message_subscribe([
                partner.id for partner in [invoice.partner_id]
                if partner not in invoice.sudo().message_partner_ids
            ])
            # Auto-schedule activity for sales invoices
            # In 18 the fields sale_activity_type_id and sale_activity_type_id has been removed
            if invoice.is_sale_document() and invoice.journal_id.activity_type_id:
                assigned_user = invoice.journal_id.sale_activity_user_id.id or invoice.invoice_user_id.id
                if assigned_user not in (self.env.ref('base.user_root').id, False):
                    invoice.activity_schedule(
                        activity_type_id=invoice.journal_id.activity_type_id.id,
                        summary=invoice.journal_id.sale_activity_note,
                        user_id=assigned_user,
                        date_deadline=min(invoice.line_ids.mapped('date_maturity') or [invoice.date])
                    )

        # Update customer and supplier ranks
        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for invoice in to_post:
            if invoice.is_sale_document():
                customer_count[invoice.partner_id] += 1
            elif invoice.is_purchase_document():
                supplier_count[invoice.partner_id] += 1
            elif invoice.move_type == 'entry':
                # Infer partner rank from account type lines
                for partner in invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable').mapped('partner_id'):
                    customer_count[partner] += 1
                for partner in invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable').mapped('partner_id'):
                    supplier_count[partner] += 1

        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Automatically mark zero-amount invoices as paid
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        )._invoice_paid_hook()

        # Trigger hooks for asset depreciation / creation / closing
        to_post._log_depreciation_asset()
        to_post.sudo()._auto_create_asset()
        # to_post._close_assets() #Removed from base

        return to_post
    # FIXME: Fix the recursive execution behaviour
    # def action_post(self):
    #     """
    #     Entry point for posting from the form button.
    #     Handles any move linked to a payment separately.
    #     """
    #     # Moves linked to payments are handled by payment posting
    #     moves_with_payments = self.filtered('origin_payment_id')
    #     other_moves = self - moves_with_payments
    #
    #     if moves_with_payments:
    #         moves_with_payments.origin_payment_id.action_post()
    #
    #     if other_moves:
    #         # Use context flag to allow asset condition logic inside _post
    #         other_moves.with_context(called_from_validation=True)._post(soft=False)
    #
    #     return False
