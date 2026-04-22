import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class CreditCardRequest(models.Model):
    _name = "credit.card.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"
    _description = "Credit Card Request"

    name = fields.Char('Name', default=_('New'), copy=False)
    narration = fields.Char('Narration', required=True)
    order_date = fields.Date('Order Date', default=lambda self: fields.Date.today())
    approve_date = fields.Date('Approve Date')

    by_employee = fields.Boolean('By Employee', default=True)
    use_analytic = fields.Boolean('Use Analytic', default=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda s: s.env.company)
    requester_emp_id = fields.Many2one('hr.employee', 'Employee Requester')
    requester_partner_id = fields.Many2one('res.partner', 'Partner Requester')
    move_id = fields.Many2one('account.move', 'Journal Entry')
    operation_account_id = fields.Many2one('account.account', 'Operation Account', default=lambda self : self.env.company.account_journal_suspense_account_id)
    operation_journal_id = fields.Many2one('account.journal', 'Operation Journal', domain=[('type', 'in', ('bank', 'cash'))])
    user_id = fields.Many2one('res.users', string='User', required=False, default=lambda self: self.env.user)

    settlement_ids = fields.One2many('expense.funding.settlement', 'card_request_id', string='Settlements')

    analytic_distribution = fields.Json()
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    journal_id =  fields.Many2one('account.journal', domain=[('type', '=', 'credit')])
    amount = fields.Float('Amount', required=True)
    settlement_amount = fields.Float('Settlement Amount', compute='_compute_settlement', store=True)
    different_amount = fields.Float('Different Amount', compute='_compute_different_amount', store=True)
    in_settlement = fields.Boolean('In Settlement', default=False, compute='_compute_settlement')
    settlement_state = fields.Selection([
        ('no', 'Not Yet'),
        ('partial', 'Partial Settlement'),
        ('full', 'Full Settlement')], string='Settlement Status', default='no', compute='_set_settlement_status')
    state = fields.Selection([
        ('new', 'New'),
        ('draft', 'Request'),
        ('approval', 'Approval'),
        ('complete', 'Complete'),
        ('return', 'Return'),
        ('reject', 'Rejected')], string='Status', default='new')

    note = fields.Text(string='Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Shared attachments')
    card_return_date = fields.Datetime('Return Date')
    move_ids = fields.Many2many('account.move', string='Moves')

    def unlink(self):
        for record in self:
            if record.state != 'new':
                raise UserError(
                    _("You cannot delete a request that has already been submitted.")
                )
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if not val.get('name', False) or val['name'] == _('New'):
                val['name'] = self.env['ir.sequence'].next_by_code('credit.card.request') or _('New')
        return super().create(vals_list)

    @api.constrains('settlement_ids')
    def _check_settlements_amount(self):
        for rec in self:
            if sum(rec.settlement_ids.mapped('amount')) > rec.amount:
                raise ValidationError(_("You cannot settle a balance higher than the Credit Card"))

    @api.depends('settlement_ids')
    def _compute_settlement(self):
        for rec in self:
            rec.settlement_amount = 0.0
            rec.different_amount = 0.0
            rec.in_settlement = False
            if rec.settlement_ids:
                rec.settlement_amount = sum(s.amount for s in rec.settlement_ids)
                if any(not settlement.is_reconciled for settlement in rec.settlement_ids):
                    rec.in_settlement = True
            rec.different_amount = rec.amount - rec.settlement_amount

    @api.depends('amount', 'settlement_amount')
    def _compute_different_amount(self):
        for rec in self:
            rec.different_amount = rec.amount - rec.settlement_amount

    def action_submit_request(self):
        self.ensure_one()
        self.state = 'draft'

    def _set_settlement_status(self):
        for rec in self:
            if 0 < rec.settlement_amount < rec.amount:
                rec.settlement_state = 'partial'
            elif rec.settlement_amount == rec.amount or rec.settlement_amount > rec.amount:
                rec.settlement_state = 'full'
            else:
                rec.settlement_state = 'no'

    @api.onchange('requester_emp_id')
    def _onchange_requester_emp_id(self):
        if self.requester_emp_id:
            name = self.requester_emp_id.name
            if not self.requester_emp_id.work_contact_id:
                self.requester_emp_id = False
                return {'warning':
                    {
                        'title': _("Warning"),
                        'message': _('Please! Add the private contact (Address) of %(name)s from employee profile', name=name)
                    }
                }
            self.requester_partner_id = self.requester_emp_id.work_contact_id
        else:
            self.requester_partner_id = False

    @api.onchange('operation_journal_id')
    def _onchange_operation_journal_id(self):
        if self.operation_journal_id:
            self.operation_account_id = self.operation_journal_id.default_account_id.id
        else:
            self.operation_account_id = self.env.company.account_journal_suspense_account_id.id

    def _prepare_debit_data(self, name, debit_account, debit_amount, partner):
        return {
            'name': name,
            'partner_id': partner.id,
            'account_id': debit_account.id,
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'analytic_distribution': self.analytic_distribution and self.analytic_distribution or False,
            'debit': debit_amount,
            'credit': 0.0,
        }

    def _prepare_credit_data(self, name, credit_account, credit_amount, partner):
        return {
            'name': name,
            'partner_id': partner.id,
            'account_id': credit_account.id,
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'analytic_distribution': self.analytic_distribution and self.analytic_distribution or False,
            'debit': 0.0,
            'credit': credit_amount,
        }

    def _prepare_move_lines_data(self, operation_account_id, amount):
        journal_id = self.journal_id
        return [
            (0, 0, self._prepare_debit_data(self.narration, journal_id.default_account_id, amount, self.requester_partner_id)),
            (0, 0, self._prepare_credit_data(self.narration, operation_account_id, amount, self.requester_partner_id))]

    def _create_account_move(self):
        if self.move_id:
            raise UserError(_("You have already created a journal entry."))
        move_id = self.env['account.move'].create([{
            'narration': self.narration,
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'move_type': 'entry'
        }])
        return move_id

    def action_approve(self):
        for rec in self:
            rec.write({'state': 'complete', 'approve_date': fields.Date.today()})
            rec.journal_id.card_holder_uid = rec.requester_emp_id
        return True

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'
        return True

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
        return True

    def action_paid(self):
        for rec in self:
            rec.state = 'complete'
        return True

    def action_return(self):
        for rec in self:
            rec.card_return_date = fields.Datetime.now()
            rec.state = 'return'
            rec.journal_id.card_holder_uid = False

    def _reconciliation(self, move_id, reconcile_move_id, account_id):
        (move_id.line_ids.filtered(lambda l: l.account_id == account_id) + reconcile_move_id.line_ids.filtered(
            lambda l: l.account_id == account_id)).reconcile()
        return True

    def card_cash_settlement(self):
        for card in self:
            # Single transaction limit for credit card
            if card.journal_id and card.journal_id.single_transaction_limit:
                for settlement in card.settlement_ids:
                    if settlement.amount and settlement.amount > card.journal_id.single_transaction_limit:
                        raise ValidationError(
                            _('Single transaction limit exceeded for this credit card journal (%.2f). Line amount: %.2f') % (
                                card.journal_id.single_transaction_limit, settlement.amount))
            journal = card.journal_id
            # Annual limit check
            if journal and journal.annual_limit:
                today = fields.Date.context_today(self)
                start_year = today.replace(month=1, day=1)
                end_year = today.replace(month=12, day=31)
                domain = [('journal_id', '=', journal.id), ('state', 'in', ('complete', 'approval')),
                          ('order_date', '>=', start_year), ('order_date', '<=', end_year)]
                approved_amount = sum(self.search(domain).mapped('amount'))
                if approved_amount + card.amount > journal.annual_limit:
                    raise ValidationError(
                        _('Annual limit exceeded for this journal (%.2f). Approved this year: %.2f') % (
                            journal.annual_limit, approved_amount))
            settlements_with_expenses = card.settlement_ids.filtered(lambda s: not s.is_reconciled and s.expense_id and s.expense_id.state == 'post')
            settlements_with_bills = card.settlement_ids.filtered(lambda s: not s.is_reconciled and s.bill_id and s.bill_id.payment_state == 'not_paid')
            settlements_without_bills = card.settlement_ids.filtered(lambda s: not s.bill_id and not s.expense_id and not s.is_reconciled)
            suspense_account_id = card.journal_id.suspense_account_id
            account_id = card.journal_id.default_account_id
            requester_id = card.requester_partner_id
            if settlements_with_expenses:
                for settlement in settlements_with_expenses:
                    expense_move_id = settlement.expense_id.account_move_ids
                    move_line = expense_move_id.line_ids.filtered(
                        lambda l: l.account_id.account_type == 'liability_payable')
                    payable_partner = move_line[0].mapped('partner_id')
                    payable_account = move_line[0].mapped('account_id')
                    payable_amount = sum(move_line.mapped('credit'))

                    adjustment_suspense_name = 'Reconcile the expense sheet from ( %s )' % card.narration

                    line_ids_for_suspense = [
                        (0, 0, card._prepare_debit_data(adjustment_suspense_name, payable_account, payable_amount,
                                                         payable_partner)),
                        (0, 0,
                         card._prepare_credit_data(adjustment_suspense_name, account_id, settlement.amount,
                                                    requester_id))
                    ]
                    move_suspense_id = self.env['account.move'].create([{
                        'narration': adjustment_suspense_name,
                        'ref': 'Credit Card [ %s ]' % card.name,
                        'journal_id': card.journal_id.id,
                        'date': fields.Date.today(),
                        'move_type': 'entry',
                        'line_ids': line_ids_for_suspense,
                        'company_id': self.env.company.id,
                    }])
                    if move_suspense_id:
                        card.move_ids = [fields.Command.link(move_suspense_id.id)]
                        move_suspense_id.action_post()
                        card._reconciliation(expense_move_id, move_suspense_id, payable_account)
                        settlement._set_is_reconcile()

            if settlements_with_bills:
                for settlement in settlements_with_bills:
                    move_line = settlement.bill_id.line_ids.filtered(
                        lambda l: l.account_id.account_type == 'liability_payable')

                    adjustment_suspense_name = 'Reconcile the bill from ( %s )' % card.narration

                    line_ids_for_suspense = [
                        (0, 0,
                         card._prepare_debit_data(adjustment_suspense_name, move_line.account_id, settlement.amount,
                                                   settlement.bill_id.partner_id)),
                        (0, 0, card._prepare_credit_data(adjustment_suspense_name, account_id,
                                                          settlement.amount,
                                                          requester_id))
                    ]
                    move_suspense_id = self.env['account.move'].create([{
                        'narration': adjustment_suspense_name,
                        'ref': 'Credit card [ %s ]' % card.name,
                        'journal_id': card.journal_id.id,
                        'date': fields.Date.today(),
                        'move_type': 'entry',
                        'line_ids': line_ids_for_suspense,
                        'company_id': self.env.company.id,
                    }])
                    if move_suspense_id:
                        card.move_ids = [fields.Command.link(move_suspense_id.id)]
                        move_suspense_id.action_post()
                        card._reconciliation(settlement.bill_id, move_suspense_id, move_line.account_id)
                        settlement._set_is_reconcile()
            if settlements_without_bills:
                if any(not line.expense_account_id for line in settlements_without_bills):
                    raise ValidationError(_("You should add expense account for any settlement line has not bill or expense"))
                line_ids = []
                adjustment_name = 'Settlements of ( %s )' % card.narration
                credit_amount = 0.0
                for settlement in settlements_without_bills:
                    credit_amount += settlement.amount
                    line_ids.append((0, 0,
                                     card._prepare_debit_data(settlement.name, settlement.expense_account_id,
                                                               settlement.amount,
                                                               requester_id)))

                line_ids.append((0, 0,
                                 card._prepare_credit_data(adjustment_name, card.journal_id.default_account_id,
                                                            credit_amount,
                                                            requester_id)))
                move_id = self.env['account.move'].create([{
                    'narration': 'Settlements of ( %s )' % card.narration,
                    'ref': 'Settlements of %s' % card.name,
                    'journal_id': card.journal_id.id,
                    'date': fields.Date.today(),
                    'move_type': 'entry',
                    'line_ids': line_ids,
                    'company_id': self.env.company.id,
                }])
                if move_id:
                    card.move_ids = [fields.Command.link(move_id.id)]
                    move_id.action_post()
                    card._reconciliation(card.move_id, move_id, account_id)
                    settlement._set_is_reconcile()

    def open_reconcile_view(self):
        action = self.move_ids._get_records_action(name="Reconciled Moves")
        action['context'] = {}
        return action