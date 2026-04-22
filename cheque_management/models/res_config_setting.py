""" Initialize Res Config Setting """

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
        Inherit Res Config Settings:
         -
    """
    _inherit = 'res.config.settings'

    # Incoming
    in_journal_id = fields.Many2one(
        string='Incoming Journal', readonly=False,
        related='company_id.in_journal_id'
    )
    checks_received_in_treasury_id = fields.Many2one(
        string='Checks received in the treasury', readonly=False,
        related='company_id.checks_received_in_treasury_id'
    )
    checks_under_collection_by_bank_id = fields.Many2one(
        string='Checks under collection by the bank', readonly=False,
        related='company_id.checks_under_collection_by_bank_id'
    )
    incoming_bounced_checks_id = fields.Many2one(
        string='Incoming Bounced checks', readonly=False,
        related='company_id.incoming_bounced_checks_id'
    )
    # Outgoing
    out_journal_id = fields.Many2one(
        string='Outgoing Journal', readonly=False,
        related='company_id.out_journal_id'
    )
    checks_issued_id = fields.Many2one(
        related='company_id.checks_issued_id', readonly=False
    )
    outgoing_bounced_checks_id = fields.Many2one(
        related='company_id.outgoing_bounced_checks_id', readonly=False
    )
    intermediate_account = fields.Many2one(
        related='company_id.intermediate_account', readonly=False
    )

    cheque_reminder_days_before_due = fields.Integer(
        related='company_id.cheque_reminder_days_before_due',
        string='Reminder Days Before Due',
        readonly=False,
        help='Number of days before due date to send reminder notification to PDC Manager'
    )
    cheque_overdue_reminder_days = fields.Integer(
        related='company_id.cheque_overdue_reminder_days',
        string='Overdue Reminder Frequency (Days)',
        readonly=False,
        help='Send reminder every X days after due date if cheque is not processed'
    )

class ResCompany(models.Model):
    """
        Inherit Res Company:
         -
    """
    _inherit = 'res.company'

    # Incoming
    in_journal_id = fields.Many2one(
        'account.journal', string='Incoming Journal',
    )
    checks_received_in_treasury_id = fields.Many2one(
        'account.account', string='Checks received in the treasury'
    )
    checks_under_collection_by_bank_id = fields.Many2one(
        'account.account', string='Checks under collection by the bank'
    )
    incoming_bounced_checks_id = fields.Many2one(
        'account.account', string='Incoming Bounced checks'
    )
    # Outgoing
    out_journal_id = fields.Many2one(
        'account.journal', string='Outgoing Journal',
    )
    checks_issued_id = fields.Many2one(
        'account.account'
    )
    outgoing_bounced_checks_id = fields.Many2one(
        'account.account'
    )
    intermediate_account = fields.Many2one('account.account')

    # Cheque Reminder Configuration Fields
    cheque_reminder_days_before_due = fields.Integer(
        string='Reminder Days Before Due',
        default=3,
        help='Number of days before due date to send reminder notification to PDC Manager'
    )
    cheque_overdue_reminder_days = fields.Integer(
        string='Overdue Reminder Frequency (Days)',
        default=3,
        help='Send reminder every X days after due date if cheque is not processed'
    )

