""" Initialize Cheque Management """
import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChequeManagement(models.Model):
    """
        Initialize Cheque Management:
         -
    """
    _name = 'cheque.management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Cheque Management'
    _check_company_auto = True
    # _sql_constraints = [
    #     ('unique_cheque_number',
    #      'UNIQUE(cheque_number)',
    #      'Cheque Number must be unique'),
    # ]

    name = fields.Char(
        readonly=False, default='New', copy=False
    )
    cheque_type = fields.Selection(
        [('incoming', 'Incoming'), ('outgoing', 'Outgoing')])
    description = fields.Char(
        required=True,
        readonly=False, states={'draft': [('readonly', False)]}
    )
    partner_type = fields.Selection(
        [('receivable', 'Receivable'),
         ('payable', 'Payable'),
         ], readonly=False, states={'draft': [('readonly', False)]},
        default='payable', required=True
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer / Vendor',
        readonly=False, states={'draft': [('readonly', False)]},
        domain=['|', ('is_company', '=', True), ('parent_id', '=', False)]
    )
    cheque_number = fields.Char(readonly=False, copy=False, required=True,
                                states={'draft': [('readonly', False)]}
                                )
    same_cheque_management_id = fields.Many2one('cheque.management', string='Cheque with same number',
                                                   compute='_compute_same_cheque_management_id', store=False)
    cheque_date = fields.Date(default=lambda self: fields.Date.today())
    check_due_date = fields.Date(
        readonly=False, states={'draft': [('readonly', False)]}
    )
    currency_id = fields.Many2one(
        'res.currency', required=True, readonly=False,
        default=lambda self: self.env.company.currency_id,
        states={'draft': [('readonly', False)]}
    )

    employee_id = fields.Many2one(
        'hr.employee', string='Check Sender To Bank',
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1),
    )
    bank_account_id = fields.Many2one(
        'account.journal', domain="[('type', '=', 'bank')]", readonly=False,
        states={'draft': [('readonly', False)]}
    )
    deposit_date = fields.Date(readonly=False)
    collected_by_another_bank_treasury = fields.Many2one(
        'account.journal', domain="[('type', '=', ['bank','cash'])]",
        string='Collected By Another Bank/Treasury', readonly=False
    )
    deducted_by_another_bank_treasury = fields.Many2one(
        'account.journal', domain="[('type', '=', ['bank','cash'])]",
        string='Deducted By Another Bank/Treasury', readonly=False
    )
    cheque_received_date = fields.Date(
        readonly=False
    )
    cheque_send_date = fields.Date(
        readonly=False,
    )
    hand_me_the_check = fields.Char()
    beneficiary_of_the_check = fields.Char(
        string='The Beneficiary Of The Check',
        readonly=False, states={'draft': [('readonly', False)]}
    )
    drawn_bank = fields.Char(
        readonly=False, states={'draft': [('readonly', False)]}
    )
    check_back = fields.Boolean(
        string='Check back ?'
    )
    back_person_name = fields.Char()
    note = fields.Text()
    move_ids = fields.Many2many(
        'account.move'
    )
    move_type = fields.Selection(
        [('out_invoice', 'Out Invoice'),
         ('in_invoice', 'In Invoice'),
         ('done', 'Done')],
        default='out_invoice',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('send_to_bank', 'Send To Bank'),
        ('deposit', 'Deposited'),
        ('bounced', 'Bounced'),
        ('return_to_partner', 'Return To Partner'),
        ('return_from_partner', 'Return From Partner'),
        ('cashed', 'Cashed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft')
    move_line_ids = fields.One2many(
        'account.move.line', 'cheque_id', readonly=False,
        copy=False, ondelete='restrict'
    )
    journal_item_count = fields.Integer(
        string='Journal Items', compute='_journal_item_count', readonly=False,
        copy=False
    )
    cash_date = fields.Date(readonly=False)
    bounced_date = fields.Date(readonly=False)
    return_to_partner_date = fields.Date(readonly=False)
    return_from_partner_date = fields.Date(readonly=False)
    currency_amount = fields.Float(
        string='Amount', required=True, readonly=False,
        states={'draft': [('readonly', False)]}
    )
    amount = fields.Float(
        compute='_compute_amount', store=1
    )
    cheque_book_id = fields.Many2one('cheque.book',
                                     domain=[('is_finished', '=', False)])
    cheque_page_number = fields.Char()
    check_transfer = fields.Selection(
        [('check', 'Partner Check'), ('expense', 'Petty Cash Check')])
    incoming_check_transfer = fields.Selection(
        [('check', 'Check')])
    transaction_number = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Report Company Currency",
        readonly=True,
    )
    purchase_order_ids = fields.Many2many('purchase.order')
    sale_order_ids = fields.Many2many('sale.order')
    account_id = fields.Many2one('account.account')
    
    # Petty Cash Check fields
    expense_allocation_ids = fields.One2many(
        'cheque.expense.allocation', 'cheque_id',
        string='Expense Allocation'
    )
    hr_expense_ids = fields.Many2many('hr.expense', string='Expense References')

    account_payment_ids = fields.One2many('account.payment',
                                          'cheque_management_id')
    count_payments = fields.Integer(compute='_compute_account_payment_count',
                                    store=True)
    batch_monetization = fields.Float()
    reminder = fields.Float()
    state_batch_monetization = fields.Selection([('1', 'Batch Monetization')],
                                                string="Payment State")
    hr_expense_id = fields.Many2one('hr.expense', string="Expense Ref")
    delivered_to = fields.Char(string="Delivered To")

    last_reminder_sent = fields.Date(
        string='Last Reminder Sent',
        readonly=True,
        help='Date when last reminder was sent'
    )
    reminder_count = fields.Integer(
        string='Reminder Count',
        default=0,
        readonly=True,
        help='Number of reminders sent for this cheque'
    )

    @api.onchange('hr_expense_id')
    def onchange_hr_expense_id(self):
        if self.hr_expense_id:
            hr_expense_id = self.hr_expense_id
            self.account_id = hr_expense_id.account_id.id
            self.currency_id = hr_expense_id.currency_id.id or self.company_currency_id.id
            self.currency_amount = hr_expense_id.total_amount_currency

    @api.onchange('expense_allocation_ids')
    def _onchange_expense_allocation_ids(self):
        """Update currency_amount when expense allocations change"""
        if self.check_transfer == 'expense' and self.expense_allocation_ids:
            self.currency_amount = sum(self.expense_allocation_ids.mapped('amount'))

    @api.depends('cheque_number')
    def _compute_same_cheque_management_id(self):
        for check_mgmt_id in self:
            check_mgmt_id.same_cheque_management_id = False
            if check_mgmt_id.cheque_number:
                # use _origin to deal with onchange()
                #active_test = False because if a partner has been deactivated you still want to raise the error,
                #so that you can reactivate it instead of creating a new one, which would loose its history.
                check_management_obj = self.with_context(active_test=False).sudo()
                domain = [
                    ('id', '!=', check_mgmt_id._origin.id), ('cheque_number', '=', check_mgmt_id.cheque_number),
                ]
                check_mgmt_id.same_cheque_management_id = check_management_obj.search(domain, limit=1).id


    # def view_batch_monetization(self):
    #     """ Smart button to run action """
    #     action = \
    #         self.env.ref('cheque_management.batch_monetization_action').sudo().read()[
    #             0]
    #     action['views'] = [
    #         (self.env.ref('cheque_management.batch_monetization_form').id,
    #          'form')]
    #     action['context'] = {'default_partner_id': self.partner_id.id,
    #                          'default_amount': self.amount - self.batch_monetization}
    #
    #     return action

    # @api.depends('account_payment_ids')
    # def _compute_account_payment_count(self):
    #     """ Compute account_payment_count value """
    #     for rec in self:
    #         rec.count_payments = len(
    #             rec.account_payment_ids.ids)

    # def action_account_payment_count_view(self):
    #     """ Smart button to run action """
    #
    #     recs = self.mapped('account_payment_ids')
    #     action = \
    #         self.env.ref(
    #             'account.action_account_payments').sudo().read()[
    #             0]
    #     if len(recs) > 1:
    #         action['domain'] = [('id', 'in', recs.ids)]
    #     elif len(recs) == 1:
    #         action['views'] = [
    #             (
    #                 self.env.ref('account.view_account_payment_form').id,
    #                 'form')]
    #         action['res_id'] = recs.ids[0]
    #
    #     else:
    #         action['views'] = [
    #             (
    #                 self.env.ref('account.view_account_payment_form').id,
    #                 'form')]
    #
    #     return action

    def open_payment_matching_screen(self):
        # Open reconciliation view for customers/suppliers
        action_values = self.env['ir.actions.act_window']._for_xml_id(
            'account_accountant.action_move_line_posted_unreconciled')
        context = ast.literal_eval(action_values['context'])
        move_line_id = False
        for move_line in self.move_line_ids:
            if move_line.account_id.reconcile:
                move_line_id = move_line.id
                break
        
        context.update({
            'company_ids': [self.company_id.id],
            'partner_ids': [self.partner_id.commercial_partner_id.id],
            'search_default_partner_id': self.partner_id.id,
        })
        
        if self.partner_id:
            if self.partner_id.customer_rank:
                context.update({'mode': 'customers'})
            elif self.partner_id.supplier_rank:
                context.update({'mode': 'suppliers'})
        else:
            context.update({'partner_ids': []})
        
        if move_line_id:
            context.update({'move_line_id': move_line_id})
        
        action_values['context'] = context
        action_values['domain'] = [('partner_id', '=', self.partner_id.id)]
        return action_values

    @api.depends('currency_id', 'currency_amount')
    def _compute_amount(self):
        """ Compute amount value """
        for rec in self:
            record = self.env['res.currency.rate'].search([
                ('currency_id', '=', rec.currency_id.id),
                ('name', '=', fields.Date.today()),
            ])
            if record:
                rec.amount = record.rate * rec.currency_amount
            else:
                rec.amount = rec.currency_id.rate * rec.currency_amount

    @api.depends('move_line_ids')
    def _journal_item_count(self):
        for rec in self:
            rec.journal_item_count = len(rec.move_line_ids)

    def reversal_entry(self):
        for check_mgmt_id in self:
            for move_id in check_mgmt_id.move_line_ids.move_id.filtered(lambda m: not m.reversal_move_ids):
                move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move",
                                                                               active_ids=move_id.ids).create({
                    'date': fields.Date.today(),
                    'journal_id': move_id.journal_id.id,
                })
                move_reversal.reverse_moves()
            check_mgmt_id.write({'state': 'cancel'})

        return True

    # @api.model
    # def create(self, vals):
    #     """ Override create method to sequence name """
    #     res = super(ChequeManagement, self).create(vals)
    #     if res.cheque_type == 'outgoing':
    #         if res.cheque_book_id:
    #             if res.cheque_book_id.next_page <= res.cheque_book_id.end:
    #                 next_page=int(res.cheque_book_id.next_page)
    #                 next_page+=1
    #                 res.cheque_book_id.next_page=next_page
    #                 if res.cheque_book_id.next_page > res.cheque_book_id.end:
    #                     res.cheque_book_id.is_finished = True
    #             else:
    #                 raise ValidationError(
    #                     _("this a cheque book is finish"))
    #     return res

    def action_confirm_wizard(self):
        """ :return Action confirm wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'confirm',
            },
            'views': [[False, 'form']]
        }

    def confirm(self):
        """ Confirm """
        if self.currency_amount <= 0:
            raise UserError(_('Amount must be greater than zero.'))

        self.name = self.env['ir.sequence'].next_by_code(
            'cheque.management') or '/'

        Move = self.env['account.move']
        if self.partner_type == 'receivable':
            account_id = self.partner_id.property_account_receivable_id
        else:
            account_id = self.partner_id.property_account_payable_id
        if self.cheque_type == 'incoming':
            if self.incoming_check_transfer == 'check':
                credit_line = {
                    'account_id': self.partner_id.property_account_receivable_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Confirm',
                    'debit': 0,
                    'credit': self.amount,
                    'amount_currency': -self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': fields.Date.today(),
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id':
                        self.env.company.checks_received_in_treasury_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Confirm',
                    'debit': self.amount,
                    'credit': 0,
                    'amount_currency': self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': fields.Date.today(),
                    'cheque_id': self.id,
                }
        else:
            if self.check_transfer == 'expense':
                # Petty Cash Check: Dr multiple expense accounts / Cr Check Issued
                if not self.expense_allocation_ids:
                    raise UserError(_('Please add expense allocation for Petty Cash Check.'))
                
                line_ids = []
                # Credit line for Check Issued
                credit_line = {
                    'account_id': self.env.company.checks_issued_id.id,
                    'name': self.name + '-' + 'Confirm',
                    'debit': 0,
                    'credit': self.amount,
                    'amount_currency': -self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': fields.Date.today(),
                    'cheque_id': self.id,
                }
                line_ids.append((0, 0, credit_line))
                
                # Debit lines for each expense account
                for allocation in self.expense_allocation_ids:
                    debit_line = {
                        'account_id': allocation.account_id.id,
                        'name': self.name + '-' + 'Confirm',
                        'debit': allocation.amount,
                        'credit': 0,
                        'amount_currency': allocation.amount,
                        'currency_id': self.currency_id.id,
                        'date_maturity': fields.Date.today(),
                        'cheque_id': self.id,
                    }
                    line_ids.append((0, 0, debit_line))
                
                move_vals = {
                    'date': self.cheque_date,
                    'journal_id': self.env.company.out_journal_id.id,
                    'ref': self.name,
                    'currency_id': self.currency_id.id,
                    'move_type': 'entry',
                    'line_ids': line_ids
                }
                move_id = Move.create(move_vals)
                move_id.action_post()
                self.create_activity()
                self.write({'cheque_received_date': fields.Date.today(), 'state': 'confirm'})
                return
            else:
                credit_line = {
                    'account_id': self.env.company.checks_issued_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Confirm',
                    'debit': 0,
                    'credit': self.amount,
                    'amount_currency': -self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': fields.Date.today(),
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id': account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Confirm',
                    'debit': self.amount,
                    'credit': 0,
                    'amount_currency': self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': fields.Date.today(),
                    'cheque_id': self.id,
                }
        move_vals = {
            'date': self.cheque_date,
            'journal_id': self.env.company.out_journal_id.id if
            self.cheque_type == 'outgoing' else
            self.env.company.in_journal_id.id,
            'ref': self.name,
            'currency_id': self.currency_id.id,
            'move_type': 'entry',
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
        }
        move_id = Move.create(move_vals)
        move_id.action_post()
        self.create_activity()
        self.write(
            {
                'cheque_received_date': fields.Date.today(),
                'state': 'confirm'
            }
        )

    def cancel(self):
        """ Cancel """
        Move = self.env['account.move']
        if self.partner_type == 'receivable':
            account_id = self.partner_id.property_account_receivable_id
        else:
            account_id = self.partner_id.property_account_payable_id

        if self.cheque_type == 'incoming':
            credit_line = {
                'account_id':
                    self.env.company.checks_received_in_treasury_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Cancel',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': fields.Date.today(),
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.bank_account_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Cancel',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': fields.Date.today(),
                'cheque_id': self.id,
            }
        else:
            credit_line = {
                'account_id': account_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Cancel',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': fields.Date.today(),
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.env.company.checks_issued_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Cancel',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': fields.Date.today(),
                'cheque_id': self.id,
            }
        move_vals = {
            'date': self.cheque_date,
            'journal_id': self.env.company.out_journal_id.id if
            self.cheque_type == 'outgoing' else
            self.env.company.in_journal_id.id,
            'ref': self.name,
            'currency_id': self.currency_id.id,
            'move_type': 'entry',
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
        }
        move_id = Move.create(move_vals)
        move_id.action_post()
        self.write({'state': 'cancel'})

    def action_cashed_wizard(self):
        """ :return Action Cashed Wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'cashed',
                'default_cash_type':
                    'in' if self.cheque_type == 'incoming' else 'out',
            },
            'views': [[False, 'form']]
        }

    def cashed(self, cash_date, collected_by_another_bank_treasury,
               deducted_by_another_bank_treasury):
        """ Cashed """
        Move = self.env['account.move']
        if self.partner_type == 'receivable':
            account_id = self.partner_id.property_account_receivable_id
        else:
            account_id = self.partner_id.property_account_payable_id
        
        if self.cheque_type == 'incoming':
            if self.state in ['confirm', 'bounced']:
                # Cashed from confirm or bounced: Dr Cash/Bank / Cr Treasury
                credit_line = {
                    'account_id': self.env.company.checks_received_in_treasury_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Cashed',
                    'debit': 0,
                    'credit': self.amount,
                    'amount_currency': -self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': cash_date,
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id': collected_by_another_bank_treasury.default_account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Cashed',
                    'debit': self.amount,
                    'credit': 0,
                    'amount_currency': self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': cash_date,
                    'cheque_id': self.id,
                }
                move_vals = {
                    'date': cash_date,
                    'journal_id': self.env.company.in_journal_id.id,
                    'ref': self.name,
                    'currency_id': self.currency_id.id,
                    'move_type': 'entry',
                    'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
                }
            elif self.state == 'return_to_partner':
                # Cashed from return_to_partner: Dr Cash/Bank / Cr A/R or A/P
                credit_line = {
                    'account_id': account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Cashed',
                    'debit': 0,
                    'credit': self.amount,
                    'amount_currency': -self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': cash_date,
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id': collected_by_another_bank_treasury.default_account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Cashed',
                    'debit': self.amount,
                    'credit': 0,
                    'amount_currency': self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': cash_date,
                    'cheque_id': self.id,
                }
                move_vals = {
                    'date': cash_date,
                    'journal_id': self.env.company.in_journal_id.id,
                    'ref': self.name,
                    'currency_id': self.currency_id.id,
                    'move_type': 'entry',
                    'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
                }
            else:
                # Cashed from other states (send_to_bank, etc)
                credit_line = {
                    'account_id': account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Cashed',
                    'debit': 0,
                    'credit': self.amount,
                    'amount_currency': -self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': cash_date,
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id': collected_by_another_bank_treasury.default_account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': self.name + '-' + 'Cashed',
                    'debit': self.amount,
                    'credit': 0,
                    'amount_currency': self.currency_amount,
                    'currency_id': self.currency_id.id,
                    'date_maturity': cash_date,
                    'cheque_id': self.id,
                }
                move_vals = {
                    'date': cash_date,
                    'journal_id': self.env.company.in_journal_id.id,
                    'ref': self.name,
                    'currency_id': self.currency_id.id,
                    'move_type': 'entry',
                    'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
                }
        else:
            # Outgoing cheque: Dr Check Issued / Cr selected treasury
            credit_line = {
                'account_id': deducted_by_another_bank_treasury.default_account_id.id,
                'partner_id': self.partner_id.id if self.check_transfer == 'check' else False,
                'name': self.name + '-' + 'Cashed',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': cash_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.env.company.checks_issued_id.id,
                'partner_id': self.partner_id.id if self.check_transfer == 'check' else False,
                'name': self.name + '-' + 'Cashed',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': cash_date,
                'cheque_id': self.id,
            }
            move_vals = {
                'date': cash_date,
                'journal_id': self.env.company.out_journal_id.id,
                'ref': self.name,
                'currency_id': self.currency_id.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
            }
        
        move_id = Move.create(move_vals)
        move_id.action_post()
        self.write({
            'cash_date': cash_date,
            'collected_by_another_bank_treasury':
                collected_by_another_bank_treasury,
            'deducted_by_another_bank_treasury':
                deducted_by_another_bank_treasury,
            'state': 'cashed'
        })

    def action_send_to_bank_wizard(self):
        """ :return Action send to bank wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'send_to_bank',
            },
            'views': [[False, 'form']]
        }

    def send_to_bank(self, cheque_send_date, bank_account_id):
        """ Send To Bank """
        Move = self.env['account.move']
        if self.cheque_type == 'incoming':
            credit_line = {
                'account_id':
                    self.env.company.checks_received_in_treasury_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Send To Bank',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': cheque_send_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id':
                    self.env.company.checks_under_collection_by_bank_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Send To Bank',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': cheque_send_date,
                'cheque_id': self.id,
            }
            move_vals = {
                'date': cheque_send_date,
                'journal_id': self.env.company.in_journal_id.id,
                'ref': self.name,
                'currency_id': self.currency_id.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            self.write(
                {
                    'cheque_send_date': cheque_send_date,
                    'bank_account_id': bank_account_id,
                    'state': 'send_to_bank',
                }
            )

    def action_in_deposit_wizard(self):
        """ :return Action In Deposit Wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'in_deposit',
            },
            'views': [[False, 'form']]
        }

    def in_deposit(self, deposit_date):
        """Incoming Deposit"""
        Move = self.env['account.move']
        if self.cheque_type == 'incoming':
            credit_line = {
                'account_id':
                    self.env.company.checks_under_collection_by_bank_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Deposit',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': deposit_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id':
                    self.bank_account_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Deposit',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': deposit_date,
                'cheque_id': self.id,
            }
            deposit_credit_line = {
                'account_id':
                    self.partner_id.property_account_receivable_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Deposit',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': deposit_date,
                'cheque_id': self.id,
            } # DEPRECATED
            deposit_debit_line = {
                'account_id':
                    self.bank_account_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Deposit',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': deposit_date,
                'cheque_id': self.id,
            } # DEPRECATED

            move_vals = {
                'date': deposit_date,
                'journal_id': self.env.company.in_journal_id.id,
                'ref': self.name,
                'currency_id': self.currency_id.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            self.write({
                'deposit_date': deposit_date,
                'state': 'deposit',
            })

    def action_out_deposit_wizard(self):
        """ :return Action Out Deposit Wizard"""
        self.ensure_one()
        if not self.bank_account_id:
            raise UserError(_('Bank Account is required!'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'out_deposit',
            },
            'views': [[False, 'form']]
        }

    def out_deposit(self, deposit_date):
        """ Outgoing Deposit """
        Move = self.env['account.move']
        if self.cheque_type == 'outgoing':
            credit_line = {
                'account_id':
                    self.bank_account_id.default_account_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Deposit',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': deposit_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.env.company.checks_issued_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Deposit',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': deposit_date,
                'cheque_id': self.id,
            }
            move_vals = {
                'date': deposit_date,
                'journal_id': self.env.company.out_journal_id.id,
                'ref': self.name,
                'currency_id': self.currency_id.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            self.write({
                'deposit_date': deposit_date,
                'state': 'deposit'
            })

    def action_in_bounced_wizard(self):
        """ :return Action In Bounced Wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'in_bounced',
            },
            'views': [[False, 'form']]
        }

    def in_bounced(self, bounced_date):
        """ Incoming Bounced"""
        Move = self.env['account.move']
        if self.partner_type == 'receivable':
            account_id = self.partner_id.property_account_receivable_id
        else:
            account_id = self.partner_id.property_account_payable_id
        if self.cheque_type == 'incoming':
            credit_line1 = {
                'account_id': self.env.company.checks_under_collection_by_bank_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Bounced',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': bounced_date,
                'cheque_id': self.id,
            }
            debit_line1 = {
                'account_id':
                    self.env.company.checks_received_in_treasury_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Bounced',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': bounced_date,
                'cheque_id': self.id,
            }
            # credit_line2 = {
            #     'account_id':
            #         self.env.company.incoming_bounced_checks_id.id,
            #     'partner_id': self.partner_id.id,
            #     'name': self.name + '-' + 'Return To Partner',
            #     'debit': 0,
            #     'credit': self.amount,
            #     'amount_currency': -self.currency_amount,
            #     'currency_id': self.currency_id.id,
            #     'date_maturity': bounced_date,
            #     'cheque_id': self.id,
            # }
            # debit_line2 = {
            #     # 'account_id': account_id.id,
            #     'partner_id': self.partner_id.id,
            #     'name': self.name + '-' + 'Return To Partner',
            #     'debit': self.amount,
            #     'credit': 0,
            #     'amount_currency': self.currency_amount,
            #     'currency_id': self.currency_id.id,
            #     'date_maturity': bounced_date,
            #     'cheque_id': self.id,
            # }
            move_vals = {
                'date': bounced_date,
                'journal_id': self.env.company.out_journal_id.id if
                self.cheque_type == 'outgoing' else
                self.env.company.in_journal_id.id,
                'ref': self.name,
                'currency_id': self.currency_id.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, credit_line1), (0, 0, debit_line1)]
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            self.write({
                'bounced_date': bounced_date,
                'state': 'bounced'
            })

    def action_out_bounced_wizard(self):
        """ :return Action Out Bounced Wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'out_bounced',
            },
            'views': [[False, 'form']]
        }

    def out_bounced(self, bounced_date):
        """ Outgoing Bounced"""
        Move = self.env['account.move']
        if self.partner_type == 'receivable':
            account_id = self.partner_id.property_account_receivable_id
        else:
            account_id = self.partner_id.property_account_payable_id
        if self.cheque_type == 'outgoing':
            credit_line1 = {
                'account_id':
                    self.env.company.outgoing_bounced_checks_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Bounced',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': bounced_date,
                'cheque_id': self.id,
            }
            debit_line1 = {
                'account_id': self.env.company.checks_issued_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Bounced',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': bounced_date,
                'cheque_id': self.id,
            }
            credit_line2 = {
                'account_id': account_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Bounced',
                'debit': 0,
                'credit': self.amount,
                'amount_currency': -self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': bounced_date,
                'cheque_id': self.id,
            }
            debit_line2 = {
                'account_id':
                    self.env.company.outgoing_bounced_checks_id.id,
                'partner_id': self.partner_id.id,
                'name': self.name + '-' + 'Bounced',
                'debit': self.amount,
                'credit': 0,
                'amount_currency': self.currency_amount,
                'currency_id': self.currency_id.id,
                'date_maturity': bounced_date,
                'cheque_id': self.id,
            }
            move_vals = {
                'date': bounced_date,
                'journal_id': self.env.company.out_journal_id.id if
                self.cheque_type == 'outgoing' else
                self.env.company.in_journal_id.id,
                'ref': self.name,
                'currency_id': self.currency_id.id,
                'move_type': 'entry',
                'line_ids': [(0, 0, credit_line1), (0, 0, debit_line1),
                             (0, 0, credit_line2), (0, 0, debit_line2)]
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            self.write({
                'bounced_date': bounced_date,
                'state': 'bounced'
            })

    def action_return_to_partner_wizard(self):
        """ :return Action return_to_partner Wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'return_to_partner',
            },
            'views': [[False, 'form']]
        }

    def return_to_partner(self, return_to_partner_date):
        """ Return To Partner """
        Move = self.env['account.move']
        if self.partner_type == 'receivable':
            account_id = self.partner_id.property_account_receivable_id
        else:
            account_id = self.partner_id.property_account_payable_id
        
        # Dr A/R or A/P / Cr Treasury
        credit_line = {
            'account_id': self.env.company.checks_received_in_treasury_id.id,
            'partner_id': self.partner_id.id,
            'name': self.name + '-' + 'Return To Partner',
            'debit': 0,
            'credit': self.amount,
            'amount_currency': -self.currency_amount,
            'currency_id': self.currency_id.id,
            'date_maturity': return_to_partner_date,
            'cheque_id': self.id,
        }
        debit_line = {
            'account_id': account_id.id,
            'partner_id': self.partner_id.id,
            'name': self.name + '-' + 'Return To Partner',
            'debit': self.amount,
            'credit': 0,
            'amount_currency': self.currency_amount,
            'currency_id': self.currency_id.id,
            'date_maturity': return_to_partner_date,
            'cheque_id': self.id,
        }
        move_vals = {
            'date': return_to_partner_date,
            'journal_id': self.env.company.in_journal_id.id,
            'ref': self.name,
            'currency_id': self.currency_id.id,
            'move_type': 'entry',
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
        }
        move_id = Move.create(move_vals)
        move_id.action_post()
        
        self.write({
            'return_to_partner_date': return_to_partner_date,
            'state': 'return_to_partner'
        })

    def action_return_from_partner_wizard(self):
        """ :return Action return_from_partner Wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cheque Date'),
            'res_model': 'cheque.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_management_id': self.id,
                'default_button_type': 'return_from_partner',
            },
            'views': [[False, 'form']]
        }

    def return_from_partner(self, return_from_partner_date):
        """ Return From Partner """
        self.write({
            'return_from_partner_date': return_from_partner_date,
            'state': 'return_from_partner'
        })

    def action_view_account_move_line(self):
        """ :return Account Move Line action """
        self.ensure_one()
        return {
            'name': _('Journal Items'),
            'view_mode': 'list,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('cheque_id', '=', self.id)],
        }

    def create_activity(self):
        """ Create Activity """
        user_ids = self.env['res.users'].search(
            [('share', '=', False)])
        for user in user_ids:
            if user.has_group('account.group_account_user'):
                self.env['mail.activity'].sudo().create(
                    {
                        'res_id': self.id,
                        'res_model': self._name,
                        'res_model_id': self.env['ir.model'].search(
                            [('model', '=', self._name)]).id,
                        'activity_type_id': self.env.ref(
                            'mail.mail_activity_data_todo').id,
                        'note': f"Cheque {self.name}",
                        'summary': f"Cheque {self.name}",
                        'date_deadline': self.check_due_date,
                        'user_id': user.id
                    })

    def send_due_date_reminder(self, reminder_type='before_due'):
        """
            Send reminder notification to PDC Manager
            :param reminder_type: 'before_due' or 'overdue'
        """
        self.ensure_one()

        # Find PDC Manager users (users with account manager rights)
        user_ids =self.env.ref('cheque_management.group_kuec_pdc_manager').users

        # Prepare notification message
        if reminder_type == 'before_due':
            subject = f'Cheque Due Date Reminder: {self.name}'
            body = f"""
                <p>Dear PDC Manager,</p>
                <p>This is a reminder that the following cheque is due soon:</p>
                <ul>
                    <li><strong>Cheque Number:</strong> {self.cheque_number or 'N/A'}</li>
                    <li><strong>Type:</strong> {dict(self._fields['cheque_type'].selection).get(self.cheque_type)}</li>
                    <li><strong>Partner:</strong> {self.partner_id.name}</li>
                    <li><strong>Amount:</strong> {self.currency_id.symbol} {self.currency_amount}</li>
                    <li><strong>Due Date:</strong> {self.check_due_date.strftime('%d-%m-%Y')}</li>
                    <li><strong>Days Until Due:</strong> {(self.check_due_date - fields.Date.today()).days}</li>
                </ul>
                <p>Please ensure timely processing of this cheque.</p>
            """
        else:  # overdue
            days_overdue = (fields.Date.today() - self.check_due_date).days
            subject = f'OVERDUE Cheque Reminder: {self.name}'
            body = f"""
                <p>Dear PDC Manager,</p>
                <p><strong style="color: red;">OVERDUE ALERT:</strong> The following cheque has not been processed:</p>
                <ul>
                    <li><strong>Cheque Number:</strong> {self.cheque_number or 'N/A'}</li>
                    <li><strong>Type:</strong> {dict(self._fields['cheque_type'].selection).get(self.cheque_type)}</li>
                    <li><strong>Partner:</strong> {self.partner_id.name}</li>
                    <li><strong>Amount:</strong> {self.currency_id.symbol} {self.currency_amount}</li>
                    <li><strong>Due Date:</strong> {self.check_due_date.strftime('%d-%m-%Y')}</li>
                    <li><strong>Days Overdue:</strong> {days_overdue}</li>
                    <li><strong>Current Status:</strong> {dict(self._fields['state'].selection).get(self.state)}</li>
                </ul>
                <p><strong>Immediate action required!</strong></p>
            """

        # Send notification to each PDC manager
        for user_id in user_ids:
            self.env['mail.activity'].sudo().create({
                'res_id': self.id,
                'res_model': self._name,
                'res_model_id': self.env['ir.model'].search([('model', '=', self._name)]).id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'note': "Automated cheque reminder",
                'summary': subject,
                'date_deadline': self.check_due_date if reminder_type == 'before_due' else fields.Date.today(),
                'user_id': user_id.id
            })

        # ---------- Send REAL EMAIL (HTML) ----------
        # Prepare email addresses
        email_list = user_ids.mapped('email')
        email_to = ",".join([e for e in email_list if e])  # Ensure valid list

        if email_to:  # Only send if emails exist
            Mail = self.env['mail.mail'].sudo()
            email = Mail.create({
                'email_to': email_to,
                'subject': subject,
                'body_html': body,  # PURE HTML, no escaping
                'auto_delete': True,
            })
            email.send()  # Sends immediately

        # ---------- Chatter Log ----------
        self.message_post(
            body=f"Cheque reminder sent to PDC Managers: {', '.join(user_ids.mapped('name'))}",
            subject=subject,
            subtype_xmlid='mail.mt_note',
            message_type='comment',
        )

        # Update reminder tracking
        self.write({
            'last_reminder_sent': fields.Date.today(),
            'reminder_count': self.reminder_count + 1
        })

        return True

    @api.model
    def _cron_send_cheque_reminders(self):
        """
        Scheduled action to check and send cheque due date reminders
        This should be called daily by a cron job
        """
        today = fields.Date.today()
        company_id = self.env['res.company'].search([('company_code', '=', 'KUEC')], limit=1)

        # Find cheques that need reminders
        # States that indicate cheque is not yet processed
        unprocessed_states = ['confirm', 'send_to_bank']

        # 1. Send reminders for cheques approaching due date
        for cheque in self.search([
            ('check_due_date', '!=', False),
            ('state', 'in', unprocessed_states),
        ]):
            if not cheque.check_due_date:
                continue

            days_until_due = (cheque.check_due_date - today).days

            # Send reminder X days before due date
            if days_until_due == company_id.cheque_reminder_days_before_due:
                # Check if reminder already sent today
                if cheque.last_reminder_sent != today:
                    cheque.send_due_date_reminder('before_due')

        # 2. Send overdue reminders
        overdue_cheques = self.search([
            ('check_due_date', '!=', False),
            ('check_due_date', '<', today),
            ('state', 'in', unprocessed_states),
        ])

        for cheque in overdue_cheques:

            # Calculate if we should send reminder today
            days_overdue = (today - cheque.check_due_date).days

            # Send reminder on first overdue day
            if days_overdue == 0 and cheque.last_reminder_sent != today:
                cheque.send_due_date_reminder('overdue')
                continue

            # Send periodic reminders based on overdue_reminder_days
            if cheque.overdue_reminder_days > 0:
                if cheque.last_reminder_sent:
                    days_since_last_reminder = (today - cheque.last_reminder_sent).days
                    if days_since_last_reminder >= cheque.cheque_overdue_reminder_days:
                        cheque.send_due_date_reminder('overdue')
                else:
                    # No reminder sent yet, send now
                    cheque.send_due_date_reminder('overdue')

        return True


class AccountMoveLine(models.Model):
    """
        Inherit Account Move Line:
         -
    """
    _inherit = 'account.move.line'

    cheque_id = fields.Many2one('cheque.management', 'Cheque Id')


class ChequeExpenseAllocation(models.Model):
    """Expense Allocation for Petty Cash Cheques"""
    _name = 'cheque.expense.allocation'
    _description = 'Cheque Expense Allocation'

    cheque_id = fields.Many2one('cheque.management', string='Cheque', required=True, ondelete='cascade')
    account_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        required=True,
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]"
    )
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='cheque_id.currency_id', readonly=True)
