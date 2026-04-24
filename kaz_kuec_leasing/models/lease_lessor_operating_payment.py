# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LeaseLessorOperatingPayment(models.Model):
    _name = 'lease.lessor.operating.payment'
    _description = 'Lessor Operating Lease Payment'
    _order = 'payment_date, id'

    contract_id = fields.Many2one('lease.lessor.contract', string='Contract', ondelete='cascade', required=True)
    payment_index = fields.Integer(string='Payment #', required=True)
    payment_date = fields.Date(string='Payment Date', required=True)
    payment_amount = fields.Monetary(string='Payment Amount', currency_field='currency_id')
    
    invoice_id = fields.Many2one('account.move', string='Invoice', domain=[('move_type', '=', 'out_invoice')])

    currency_id = fields.Many2one(related='contract_id.currency_id', store=True, readonly=True)

    def action_create_rental_invoice(self):
        """Create rental income invoice for this payment."""
        self.ensure_one()
        contract = self.contract_id
        if not contract.account_rental_income_id:
            raise UserError(_('Please configure Rental Income Account on the contract.'))
        if self.invoice_id:
            return self.action_view_invoice()

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': contract.lessee_id.id,
            'invoice_date': self.payment_date,
            'invoice_line_ids': [
                (0, 0, {
                    'name': _('Rental Income - %s (Payment %d)') % (contract.asset_id.name, self.payment_index),
                    'account_id': contract.account_rental_income_id.id,
                    'price_unit': self.payment_amount,
                })
            ],
            'invoice_origin': contract.name,
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.invoice_id.id
        action['context'] = {'default_move_type': 'out_invoice'}
        return action
