# -*- coding: utf-8 -*-

from . import certificate_wizard
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrInternshipRewardWizard(models.TransientModel):
    _name = 'hr.internship.reward.wizard'
    _description = 'Reward Recommendation Wizard'

    internship_id = fields.Many2one(
        'hr.internship',
        string='Internship',
        required=True
    )

    reward_type = fields.Selection(
        [
            ('monetary', 'Monetary'),
            ('gift', 'Gift'),
            ('both', 'Both (Monetary + Gift)'),
        ],
        string='Reward Type',
        required=True
    )

    amount = fields.Float(
        string='Amount (AED)',
        required=True,
        default=0
    )

    gift_description = fields.Char(
        string='Gift Description',
        help='Describe the gift if applicable'
    )

    reason = fields.Text(
        string='Reason for Reward',
        required=True,
        placeholder='Explain why this intern deserves this reward'
    )

    def action_create_reward(self):
        """Create reward record"""
        self.ensure_one()
        
        if self.amount > 10000:
            raise ValidationError(_('Reward amount cannot exceed AED 10,000'))
        
        if self.amount < 0:
            raise ValidationError(_('Reward amount must be positive'))
        
        reward = self.env['hr.internship.reward'].create({
            'internship_id': self.internship_id.id,
            'reward_type': self.reward_type,
            'amount': self.amount,
            'gift_description': self.gift_description,
            'reason': self.reason,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.reward',
            'res_id': reward.id,
            'view_mode': 'form',
        }


class HrInternshipRewardRejectWizard(models.TransientModel):
    _name = 'hr.internship.reward.reject.wizard'
    _description = 'Reward Rejection Wizard'

    reward_id = fields.Many2one(
        'hr.internship.reward',
        string='Reward',
        required=True
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        placeholder='Explain why this reward is rejected'
    )

    def action_reject(self):
        """Reject reward"""
        self.ensure_one()
        self.reward_id._reject_reward(self.rejection_reason)


class HrInternshipPaymentWizard(models.TransientModel):
    _name = 'hr.internship.payment.wizard'
    _description = 'Payment Wizard'

    internship_id = fields.Many2one(
        'hr.internship',
        string='Internship',
        required=True
    )

    payment_type = fields.Selection(
        [
            ('reward', 'Reward Payment'),
            ('stipend', 'Stipend Payment'),
        ],
        string='Payment Type',
        required=True,
        default='reward'
    )

    amount = fields.Float(
        string='Amount (AED)',
        required=True,
        compute='_compute_amount'
    )

    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        domain="[('deprecated', '=', False)]"
    )

    payment_method = fields.Selection(
        [
            ('cash', 'Cash'),
            ('bank', 'Bank Transfer'),
        ],
        string='Payment Method',
        required=True
    )

    bank_account_id = fields.Many2one(
        'account.account',
        string='Bank/Cash Account',
        required=True,
        domain="[('account_type', 'in', ['asset_cash', 'asset_bank']), ('deprecated', '=', False)]"
    )

    memo = fields.Char(string='Memo/Reference')

    @api.depends('internship_id', 'payment_type')
    def _compute_amount(self):
        for wizard in self:
            if wizard.payment_type == 'reward':
                approved_rewards = wizard.internship_id.reward_ids.filtered(lambda r: r.state == 'approved')
                wizard.amount = sum(r.amount for r in approved_rewards)
            elif wizard.payment_type == 'stipend':
                wizard.amount = wizard.internship_id.total_amount
            else:
                wizard.amount = 0

    def action_create_payment(self):
        """Create payment journal entry"""
        self.ensure_one()
        
        if self.amount <= 0:
            raise UserError(_('Amount must be greater than zero'))
        
        move_vals = {
            'move_type': 'entry',
            'date': fields.Date.today(),
            'ref': self.memo or f'Payment for {self.internship_id.name}',
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_id.id,
                    'debit': self.amount,
                    'credit': 0,
                    'name': f'{self.payment_type.capitalize()} - {self.internship_id.name}',
                }),
                (0, 0, {
                    'account_id': self.bank_account_id.id,
                    'debit': 0,
                    'credit': self.amount,
                    'name': f'{self.payment_method.capitalize()} - {self.internship_id.name}',
                }),
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        
        # Update internship with payment entry
        self.internship_id.payment_move_id = move.id
        
        # Mark approved rewards as paid
        if self.payment_type == 'reward':
            approved_rewards = self.internship_id.reward_ids.filtered(lambda r: r.state == 'approved')
            for reward in approved_rewards:
                reward.state = 'paid'
                reward.payment_move_id = move.id
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }
