# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrInternshipReward(models.Model):
    _name = 'hr.internship.reward'
    _description = 'Internship Reward'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, index=True,
                                 help='Company to which this reward record belongs')

    internship_id = fields.Many2one('hr.internship', required=True, ondelete='cascade',
                                    tracking=True,
                                    help='The internship for which reward is being nominated')
    name = fields.Char(required=True, string='Reward Title',
                       help='Name or title of the reward')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending CEO Approval'),
        ('approved', 'Approved'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True, help='Current approval state of the reward')

    # Reward Details
    reward_type = fields.Selection([
        ('monetary', 'Monetary'),
        ('gift', 'Gift'),
        ('both', 'Both'),
    ], required=True, tracking=True, help='Type of reward: cash, physical gift, or both')

    amount = fields.Float(default=0, string='Monetary Amount (AED)', tracking=True,
                          help='Amount in AED (max AED 10,000)')
    gift_description = fields.Char(string='Gift Description',
                                   help='Description of the gift (e.g., tablet, certificate)')
    reason = fields.Text(required=True, string='Reason for Reward',
                         help='Justification for nominating this reward')

    rejection_reason = fields.Text(string='Rejection Reason',
                                   help='CEO reason for rejecting the reward')
    # Payment Integration
    payment_reference = fields.Char(string='Payment Reference',
                                    help='Reference for accounting/payroll system')
    payment_date = fields.Date(help='Date when reward was paid')

    # Validation
    max_amount = fields.Float(default=10000, string='Maximum Reward Amount (AED)',
                              help='Maximum allowed reward amount (can be overridden in Employee Settings)')

    @api.constrains('amount', 'internship_id')
    def _check_amount_limit(self):
        """Ensure total reward amount for an internship doesn't exceed configured max"""
        max_limit = self.company_id.reward_max_amount
        for record in self:
            if record.reward_type == 'gift':
                # Skip validation for gift-only rewards (no monetary amount)
                continue

            # Calculate total rewards for this internship (including current record)
            all_rewards = self.search([
                ('internship_id', '=', record.internship_id.id),
                ('reward_type', 'in', ['monetary', 'both']),
                ('state', '!=', 'rejected')
            ]).mapped('amount')
            total_amount = sum(all_rewards)

            if total_amount > max_limit:
                raise models.ValidationError(
                    _('Total reward amount for internship %s exceeds maximum limit of AED %.2f. Current total: AED %.2f')
                    % (record.internship_id.name, max_limit, total_amount)
                )

    def action_submit_for_approval(self):
        """Submit reward for CEO approval"""
        self.state = 'pending_approval'

    def action_approve(self):
        """CEO approves reward"""
        self.state = 'approved'

    def action_reject(self):
        """CEO rejects reward"""
        self.state = 'rejected'

    def action_notify_accounting(self):
        """Notify accounting team and move to in_payment state"""
        self.state = 'in_payment'
        self.message_post(body=_("Accounting team has been notified for payment processing."))

        # Create activity for accounting team to process payment
        self.activity_schedule(
            activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
            summary=_('Process Payment for Reward: %s') % self.name,
            note=_(
                'Reward approved and ready for payment processing.\n\nInternship: %s\nAmount: AED %.2f\nPayment Reference: %s') % (
                     self.internship_id.name,
                     self.amount,
                     self.payment_reference or 'To be generated'
                 ),
            user_id=self.env['res.groups'].sudo().search([('name', '=', 'Invoicing / Bank')],
                                                         limit=1).users[:1].id or self.env.user.id
        )

    def action_mark_as_paid(self):
        """Mark reward as paid"""
        self.state = 'paid'
        self.payment_date = fields.Date.today()
        self.message_post(body=_("Reward marked as paid."))
