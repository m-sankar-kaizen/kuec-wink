from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'

    show_credit_control_warning = fields.Boolean(compute='_check_credit_control_limit')
    show_credit_control_block = fields.Boolean(compute='_check_credit_control_limit')
    partner_debit_warning = fields.Text(
        compute='_compute_partner_debit_warning',
    )
    partner_debit = fields.Monetary(compute='_compute_partner_debit')

    @api.depends('company_id', 'partner_id', 'amount_total')
    def _compute_partner_debit_warning(self):
        for order in self:
            order.with_company(order.company_id)
            order.partner_debit_warning = ''
            show_warning = order.state in ('draft', 'sent') and \
                           order.company_id.account_use_credit_limit
            if show_warning:
                order.partner_debit_warning = self.env['account.move']._build_debit_warning_message(
                    order.sudo(),  # ensure access to `credit` & `credit_limit` fields
                    current_amount=order.amount_total,
                )

    def _build_debit_warning_message(self, record, current_amount=0.0, exclude_current=False, exclude_amount=0.0):
        """ Build the warning message that will be displayed in a yellow banner on top of the current record
            if the partner exceeds a credit limit (set on the company or the partner itself).
            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param current_amount (float):  The partner's outstanding credit amount from the current document.
            :param exclude_current (bool):  DEPRECATED in favor of parameter `exclude_amount`:
                                            Whether to exclude `current_amount` from the credit to invoice.
            :param exclude_amount (float):  The amount to subtract from the partner's `credit_to_invoice`.
                                            Consider the warning on a draft invoice created from a sales order.
                                            After confirming the invoice the (partial) amount (on the invoice)
                                            stemming from sales orders will be substracted from the `credit_to_invoice`.
                                            This will reduce the total credit of the partner.
                                            This parameter is used to reflect this amount.
            :return (str):                  The warning message to be showed.
        """
        partner_id = record.partner_id.commercial_partner_id
        credit_to_invoice =  exclude_amount
        total_credit = abs(partner_id.debit) + credit_to_invoice + abs(current_amount)
        if not partner_id.debit_limit or total_credit <= partner_id.debit_limit:
            return ''
        msg = _(
            '%(partner_name)s has reached its Debit limit of: %(credit_limit)s',
            partner_name=partner_id.name,
            credit_limit=formatLang(self.env, partner_id.debit_limit, currency_obj=record.company_id.currency_id)
        )
        total_debit_formatted = formatLang(self.env, total_credit, currency_obj=record.company_id.currency_id)
        if credit_to_invoice > 0 and current_amount > 0:
            return msg + '\n' + _(
                'Total amount due (including sales orders and this document): %(total_credit)s',
                total_credit=total_debit_formatted
            )
        elif credit_to_invoice > 0:
            return msg + '\n' + _(
                'Total amount due (including sales orders): %(total_credit)s',
                total_credit=total_debit_formatted
            )
        elif current_amount > 0:
            return msg + '\n' + _(
                'Total amount due (including this document): %(total_credit)s',
                total_credit=total_debit_formatted
            )
        else:
            return msg + '\n' + _(
                'Total amount due: %(total_credit)s',
                total_credit=total_debit_formatted
            )

    @api.depends('partner_id')
    def _compute_partner_credit(self):
        for move in self:
            move.partner_debit = move.partner_id.commercial_partner_id.debit

    def action_post(self):
        self._check_credit_control_limit() # Re-check before posting
        self._show_credit_control_block()
        return super().action_post()

    def _post(self, soft=True):
        """Override to check overdraft before posting"""
        self._check_credit_control_limit()
        self._show_credit_control_block()
        return super()._post(soft=soft)

    def _show_credit_control_block(self):
        for record in self:
            if record.show_credit_control_block:
                raise UserError(
                    _("Transaction denied. Overdraft is not permitted for this account or partner block limit reached.")
                )
            # Additional partner block enforcement: if partner block limit is enabled and exceeded, block posting
            partner = record.partner_id.commercial_partner_id
            if partner and partner.use_partner_block_limits:
                # For customer invoices (receivables)
                if record.move_type in ('out_invoice', 'out_refund'):
                    total_receivable = abs(partner.debit)
                    limit = partner.receivable_block_limit or 0.0
                    if limit and total_receivable >= limit:
                        raise UserError(_("Transaction denied. Partner reached receivable block limit: %s") % (limit,))
                # For vendor bills (payables)
                if record.move_type in ('in_invoice', 'in_refund'):
                    total_payable = abs(partner.debit)
                    limit = partner.payable_block_limit or 0.0
                    if limit and total_payable >= limit:
                        raise UserError(_("Transaction denied. Partner reached payable block limit: %s") % (limit,))

    @api.depends('line_ids')
    def _check_credit_control_limit(self):
        """Override to check credit control limit"""
        self.show_credit_control_warning = False
        self.show_credit_control_block = False
        for move in self:
            if move.state != 'draft':
                continue
            # Get all liquidity accounts involved in this move that have credit limit control enabled
            liquidity_accounts = move.line_ids.mapped('account_id').filtered(
                lambda a: a.credit_limit_control
            )
            if not liquidity_accounts:
                continue

            for account in liquidity_accounts:
                # Calculate current balance
                current_balance = account.current_balance

                # Calculate the impact of this move on the account
                move_lines = move.line_ids.filtered(
                    lambda l: l.account_id == account
                )

                balance_change = sum(move_lines.mapped('balance'))
                projected_balance = current_balance + balance_change

                # Check if balance would go below allowed limit
                if projected_balance < -account.allowed_limit:
                    move.show_credit_control_warning = False
                    move.show_credit_control_block = True
                    break

                # Warning Logic (only if limit > 0, otherwise hard block at 0 is enough)
                if account.allowed_limit > 0:
                    warning_level = account.allowed_limit * move.company_id.credit_control_warning_limit / 100
                    if projected_balance < -warning_level:
                        move.show_credit_control_warning = True
                        move.show_credit_control_block = False
