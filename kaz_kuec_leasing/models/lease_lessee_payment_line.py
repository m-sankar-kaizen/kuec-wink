# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LeaseLesseePaymentLine(models.Model):
    _name = 'lease.lessee.payment.line'
    _description = 'Lease Lessee Payment Line'
    _order = 'payment_date asc'

    contract_id = fields.Many2one(
        'lease.lessee.contract',
        string='Lease Contract',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        help='Date when the lease payment is due'
    )
    
    opening_liability = fields.Monetary(
        string='Opening Liability',
        currency_field='currency_id',
        help='Lease liability at the beginning of the period'
    )
    
    interest_amount = fields.Monetary(
        string='Interest Amount',
        currency_field='currency_id',
        help='Interest expense for the period'
    )
    
    principal_amount = fields.Monetary(
        string='Principal Amount',
        currency_field='currency_id',
        help='Principal repayment (reduction of lease liability)'
    )
    
    total_payment = fields.Monetary(
        string='Total Payment',
        currency_field='currency_id',
        help='Total payment amount (principal + interest)'
    )
    
    closing_liability = fields.Monetary(
        string='Closing Liability',
        currency_field='currency_id',
        help='Lease liability at the end of the period'
    )
    
    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        domain="[('move_type', '=', 'in_invoice')]",
        readonly=True,
        help='Related vendor bill for this payment'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='contract_id.currency_id',
        store=True
    )
    
    state = fields.Selection(
        related='vendor_bill_id.state',
        string='Bill Status',
        store=True
    )
    
    def action_create_vendor_bill(self):
        """Create vendor bill for the lease payment"""
        for line in self:
            if line.vendor_bill_id:
                raise UserError(_('Vendor bill already exists for this payment.'))
            
            contract = line.contract_id
            
            # Prepare bill lines
            bill_lines = []
            
            # Principal line (reduces lease liability)
            bill_lines.append((0, 0, {
                'name': f'Principal Payment - {contract.asset_description}',
                'account_id': contract.account_lease_liability_id.id,
                'quantity': 1,
                'price_unit': line.principal_amount,
                'tax_ids': [(6, 0, [])],
            }))
            
            # Interest line (expense)
            bill_lines.append((0, 0, {
                'name': f'Interest Expense - {contract.asset_description}',
                'account_id': contract.account_interest_expense_id.id,
                'quantity': 1,
                'price_unit': line.interest_amount,
                'tax_ids': [(6, 0, [])],
            }))
            
            # Create vendor bill
            bill_vals = {
                'move_type': 'in_invoice',
                'partner_id': contract.lessor_id.id,
                'invoice_date': line.payment_date,
                'date': line.payment_date,
                'ref': f'{contract.name} - Payment {line.payment_date}',
                'invoice_line_ids': bill_lines,
            }
            
            bill = self.env['account.move'].create(bill_vals)
            line.vendor_bill_id = bill.id
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Vendor Bill'),
                'res_model': 'account.move',
                'res_id': bill.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_view_vendor_bill(self):
        """Open the related vendor bill"""
        self.ensure_one()
        if not self.vendor_bill_id:
            raise UserError(_('No vendor bill exists for this payment.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': self.vendor_bill_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
