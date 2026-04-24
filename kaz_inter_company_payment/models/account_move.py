from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_intercompany_payment = fields.Boolean(
        string='Is Intercompany Payment', copy=False)
    intercompany_paid_amount = fields.Monetary(
        currency_field='currency_id', string='Intercompany Paid')

    other_intercompany_move = fields.Boolean(
        string="Intercompany other company Move")

    cheque_due_date = fields.Date()

    cheque_number = fields.Char()


class AccountMove(models.Model):
    _inherit = 'account.move.line'

    intercompany_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Intercompany Move",
        related="payment_id.intercompany_move_id",
        store=True,
    )
    intercompany_cheque_due_date = fields.Date(
        string="Cheque Due Date",
        related="intercompany_move_id.cheque_due_date",
        store=True,
    )

    intercompany_cheque_number = fields.Char(
        string="Cheque Number",
        related="intercompany_move_id.cheque_number",
        store=True,
    )

    ico_cheque_due_date = fields.Date(
        string="ico Cheque Due Date",
        related="move_id.cheque_due_date",
        store=True, readonly=False,
    )
    ico_cheque_number = fields.Char(
        string="ico Cheque Number",
        related="move_id.cheque_number",
        store=True, readonly=False,
    )
