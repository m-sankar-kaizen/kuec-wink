# -*- coding: utf-8 -*-
from odoo import fields, models, _, Command, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)




class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    is_readonly = fields.Boolean(string='Is Readonly')
    is_approved = fields.Boolean(string='Is Approved')
    write_off_id = fields.Many2one('write.off.request', string='Write Off')

    @api.depends('early_payment_discount_mode', 'write_off_id')
    def _compute_payment_difference_handling(self):
        for wizard in self:
            if wizard.write_off_id:
                wizard.payment_difference_handling = 'reconcile'
            elif wizard.can_edit_wizard:
                wizard.payment_difference_handling = 'reconcile' if wizard.early_payment_discount_mode else 'open'
            else:
                wizard.payment_difference_handling = False

    def _validate_write_off(self):
        invoice_id = self._context.get('active_id')
        _logger.info("Validate write-off - active_id (invoice_id): %s",
                     invoice_id)

        if not invoice_id:
            _logger.warning("No active_id found in context: %s", self._context)
            return
        _logger.debug("Context during write-off validation: %s", self._context)
        if self._context.get('default_writeoff_account_id'):
            write_off_id = self.env['write.off.request'].browse(invoice_id)
            invoice_id = write_off_id.account_move_id.id
            _logger.info("Write-off flow detected. Resolved invoice_id: %s",
                         invoice_id)

        invoice = self.env['account.move'].browse(invoice_id)

        blocking_write_offs = invoice.write_off_ids.filtered(
            lambda w: w.kuec_approval_state not in ('rejected', 'cancel', 'approved')
        )

        if blocking_write_offs:
            states = ', '.join(
                dict(self.env['write.off.request']._fields['kuec_approval_state'].selection)
                .get(w.kuec_approval_state, w.kuec_approval_state)
                for w in blocking_write_offs
            )

            raise UserError(_(
                "A Write-Off Request already exists for this document and is currently in the following state(s):\n"
                "%s\n\n"
                "Please approve, reject, or cancel the existing Write-Off Request before creating a new one."
            ) % states)

    def action_create_payments(self):
        self._validate_write_off()
        return super().action_create_payments()

    def _create_payment_vals_from_batch(self, batch_result):
        res = super()._create_payment_vals_from_batch(batch_result)
        if self.write_off_id:
            res['write_off_id'] = self.write_off_id.id
        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result)
        if self.write_off_id:
            res['write_off_id'] = self.write_off_id.id
        return res


    def action_submit_request(self):
        self.ensure_one()
        self._validate_write_off()
        invoice_id = self._context.get('active_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _("Write Off Request"),
            'view_mode': 'form',
            'res_model': 'write.off.request',
            'views': [(False, 'form')],
            'context': {
                'default_account_move_id': invoice_id,
                'default_journal_id': self.journal_id.id,
                'default_payment_method_line_id': self.payment_method_line_id.id,
                'default_partner_bank_id': self.partner_bank_id.id,
                'default_currency_id': self.currency_id.id,
                'default_writeoff_account_id': self.writeoff_account_id.id,
                'default_writeoff_label': self.writeoff_label,
                'default_payment_type': self.payment_type,
                'default_amount': self.amount,
                'default_payment_date': self.payment_date,
                'default_communication': self.communication,
                'default_payment_difference': self.payment_difference,
                'default_manual_currency_rate': self.manual_currency_rate,
                'default_line_ids': [
                    Command.set(self.line_ids.ids)
                ],
                'default_is_readonly': True,
            }
        }
