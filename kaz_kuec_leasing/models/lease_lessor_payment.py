# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LeaseLessorPaymentLine(models.Model):
    _name = 'lease.lessor.payment.line'
    _description = 'Lessor Lease Payment Line'
    _order = 'payment_date, id'

    contract_id = fields.Many2one('lease.lessor.contract', string='Contract', ondelete='cascade', required=True)
    year_index = fields.Integer(string='Year', required=True)
    payment_date = fields.Date(string='Payment Date', required=True)

    opening_receivable = fields.Monetary(string='Opening Receivable', currency_field='currency_id')
    interest_amount = fields.Monetary(string='Interest', currency_field='currency_id')
    principal_amount = fields.Monetary(string='Principal', currency_field='currency_id')
    total_payment = fields.Monetary(string='Total Payment', currency_field='currency_id')
    closing_receivable = fields.Monetary(string='Closing Receivable', currency_field='currency_id')

    invoice_id = fields.Many2one('account.move', string='Invoice', domain=[('move_type', '=', 'out_invoice')])
    payment_move_id = fields.Many2one('account.move', string='Payment Move')

    currency_id = fields.Many2one(related='contract_id.currency_id', store=True, readonly=True)

    def action_create_customer_invoice(self):
        """Create customer invoice per IFRS 16:
        Dr Accounts Receivable (Total Payment)
           Cr Lease Receivable (Principal)
           Cr Interest Income (Interest)
        """
        self.ensure_one()
        contract = self.contract_id
        
        if contract.lease_type != 'finance':
            raise UserError(_('This action is only for Finance Lease.'))
        
        if not contract.account_interest_income_id:
            raise UserError(_('Please configure Interest Income account on the contract.'))
        
        if not contract.account_lease_receivable_id:
            raise UserError(_('Please configure Lease Receivable account on the contract.'))
        
        if self.invoice_id:
            return self.action_view_invoice()

        # Use partner's receivable account for AR
        receivable_account = contract.lessee_id.property_account_receivable_id
        if not receivable_account:
            raise UserError(_('Please configure Account Receivable for partner %s.') % contract.lessee_id.name)

        # Create Customer Invoice with invoice lines
        invoice_lines = []
        
        # Principal reduction line - uses Lease Receivable account (will be credited)
        if self.principal_amount:
            invoice_lines.append((0, 0, {
                'name': _('Lease Payment (Principal) - Year %s') % self.year_index,
                'account_id': contract.account_lease_receivable_id.id,
                'quantity': 1,
                'price_unit': self.principal_amount,
            }))
        
        # Interest income line - uses Interest Income account (will be credited)
        if self.interest_amount:
            invoice_lines.append((0, 0, {
                'name': _('Interest Income - Year %s') % self.year_index,
                'account_id': contract.account_interest_income_id.id,
                'quantity': 1,
                'price_unit': self.interest_amount,
            }))

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': contract.lessee_id.id,
            'invoice_date': self.payment_date,
            'invoice_line_ids': invoice_lines,
            'ref': _('%s - Payment Year %s') % (contract.name, self.year_index),
        }
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        self.invoice_id = invoice.id
        return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.invoice_id.id
        return action
