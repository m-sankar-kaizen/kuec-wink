# -*- coding: utf-8 -*-
from odoo import fields, models, _, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    delivery_type = fields.Selection(
        selection=[
            ('general', 'General'),
            ('project', 'Project'),
            ('retainer', 'Retainer'),
        ],
        string='Delivery Type',
        default='general',
    )

    @api.model
    def default_get(self, fields_list):
        """Populate delivery_type from the source invoice for WINK companies."""
        import logging
        res = super().default_get(fields_list)
        logging.info(f"resres: {res}")
        if self.env.company.company_code == 'WINK':
            active_id = self._context.get('active_id')
            logging.info(f"active_id active_id: {active_id}")
            if active_id:
                invoice = self.env['account.move'].browse(active_id)
                logging.info(f"invoice invoice: {invoice}")
                res['delivery_type'] = invoice.delivery_model or 'general'
                logging.info(f"invoice invoice.delivery_model: {invoice.delivery_model}")
                logging.info(f"res: {res}")

        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        """Pass delivery_type, from_bill flag, and bill lines to the payment vals."""
        res = super()._create_payment_vals_from_wizard(batch_result)
        if self.company_code == 'WINK':
            res['delivery_type'] = self.delivery_type or 'general'
            res['from_bill'] = True
            if res['delivery_type'] != 'general':
                bill_lines = batch_result.get('lines', self.env['account.move.line'])
                if bill_lines:
                    res['reconcile_move_line_ids'] = [fields.Command.set(bill_lines.ids)]
        return res

    def _create_payment_vals_from_batch(self, batch_result):
        """Pass delivery_type and from_bill flag for batch-created payments."""
        res = super()._create_payment_vals_from_batch(batch_result)
        if self.company_code == 'WINK':
            res['delivery_type'] = self.delivery_type or 'general'
            res['from_bill'] = True
            if res['delivery_type'] != 'general':
                bill_lines = batch_result.get('lines', self.env['account.move.line'])
                if bill_lines:
                    res['reconcile_move_line_ids'] = [fields.Command.set(bill_lines.ids)]
        return res

    def _post_payments(self, to_process, edit_mode=False):
        """Skip posting for WINK project/retainer payments — they need approval first."""
        if self.company_code != 'WINK':
            return super()._post_payments(to_process, edit_mode)
        general = [v for v in to_process if v['payment'].delivery_type == 'general']
        if general:
            super()._post_payments(general, edit_mode)

    def _reconcile_payments(self, to_process, edit_mode=False):
        """Skip reconciliation for WINK non-general payments — handled after approval."""
        if self.company_code != 'WINK':
            return super()._reconcile_payments(to_process, edit_mode)
        general = [v for v in to_process if v['payment'].delivery_type == 'general']
        if general:
            super()._reconcile_payments(general, edit_mode)
