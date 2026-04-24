# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LeaseLessorContract(models.Model):
    _name = 'lease.lessor.contract'
    _description = 'Lessor Lease Contract (IFRS 16)'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contract Reference', required=True, copy=False, readonly=True, default='New')
    lease_type = fields.Selection([
        ('operating', 'Operating Lease'),
        ('finance', 'Finance Lease'),
    ], string='Lease Type', required=True, default='operating')

    lessee_id = fields.Many2one('res.partner', string='Lessee', required=True, 
                                 help='The customer who is leasing the asset from KUEC')
    asset_id = fields.Many2one('account.asset', string='Asset Leased', required=True, 
                                domain="[('state', '=', 'open'), ('is_leased', '=', False)]",
                                help='The fixed asset being leased to the customer')
    date_start = fields.Date(string='Lease Start Date', required=True,
                              help='Date when the lease period begins and asset is transferred to lessee')
    date_end = fields.Date(string='Lease End Date', required=True,
                            help='Date when the lease period ends')
    lease_term_years = fields.Integer(string='Lease Term (Years)', compute='_compute_lease_term_years', store=True,
                                       help='Total lease period in years, automatically calculated from start and end dates')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('running', 'Running'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True,
       help='Draft: Initial state, editable. Running: Asset marked as leased, accounting entries created. Closed: All invoices/entries reversed')

    payment_frequency = fields.Selection([
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
    ], string='Payment Frequency', required=True, default='annual',
       help='How often the lessee makes lease payments: Annual (once per year) or Monthly (12 times per year)')

    # Operating lease amount
    operating_payment_amount = fields.Monetary(string='Operating Lease Payment Amount', currency_field='currency_id',
                                                help='Fixed payment amount per period for operating lease rental')

    # Finance lease amounts
    total_lease_payments = fields.Monetary(
        string='Total Lease Payments', 
        currency_field='currency_id',
        help='Total cash the lessee will pay over the entire lease term. Formula: Payment Amount × Number of Periods'
    )
    present_value = fields.Monetary(
        string='Present Value (PV) of Lease Payments', 
        currency_field='currency_id',
        compute='_compute_present_value', store=True, readonly=True,
        help='The discounted value of all future lease payments using the Discount Rate. This becomes the Lease Receivable. Formula: PV = Σ(Payment / (1 + r)^n)'
    )
    asset_book_value = fields.Monetary(
        string='Asset Book Value (to Derecognize)', 
        currency_field='currency_id',
        compute='_compute_asset_book_value', store=True,
        help='Current book value of the asset (Original Value - Accumulated Depreciation). This amount will be removed from Fixed Asset account at lease commencement.'
    )
    discount_rate = fields.Float(
        string='Discount Rate (%)', 
        digits=(16, 4), 
        default=5.0,
        help='The interest rate used to discount lease payments and calculate interest income each year. Typically the implicit rate or incremental borrowing rate.'
    )
    deferred_interest_total = fields.Monetary(
        string='Deferred Interest Income', 
        currency_field='currency_id',
        compute='_compute_deferred_interest', store=True, readonly=True,
        help='Unearned future interest income. Formula: Deferred Interest = Total Lease Payments − Present Value. Recognized gradually over lease term.'
    )

    terms_html = fields.Html(string='Terms and Conditions')

    # Accounting setup - Operating Lease
    account_rental_income_id = fields.Many2one('account.account', string='Rental Income Account',
                                                help='Income account to credit when creating operating lease rental invoices')
    journal_lease_id = fields.Many2one('account.journal', string='Lease Journal', domain=[('type', '=', 'general')],
                                        help='General journal used for finance lease initial recognition entry only')

    # Accounting setup - Finance Lease
    account_lease_receivable_id = fields.Many2one('account.account', string='Lease Receivable Account',
                                                   help='Asset account for Net Investment in Lease (PV of future lease payments). Recognized at commencement.')
    account_fixed_asset_id = fields.Many2one('account.account', string='Fixed Asset Account (Derecognition)',
                                              compute='_compute_asset_accounts', store=True,
                                              help='Account to credit when removing the leased asset from books at lease start. Auto-filled from selected asset.')
    account_selling_profit_id = fields.Many2one('account.account', string='Selling Profit/Loss Account',
                                                 help='Income/Expense account for difference between PV and Asset Book Value at commencement')
    account_deferred_interest_id = fields.Many2one('account.account', string='Deferred Interest Income Account',
                                                    help='NOT used in initial entry per IFRS 16. Interest is recognized over time via invoices.')
    account_interest_income_id = fields.Many2one('account.account', string='Interest Income Account',
                                                  help='Revenue account credited each period when recognizing earned interest income')

    payment_line_ids = fields.One2many('lease.lessor.payment.line', 'contract_id', string='Finance Payment Schedule', copy=False)
    operating_payment_line_ids = fields.One2many('lease.lessor.operating.payment', 'contract_id', string='Operating Payment Schedule', copy=False)
    
    initial_recognition_move_id = fields.Many2one('account.move', string='Initial Recognition Entry', readonly=True, copy=False,
                                                    help='Journal entry created at lease commencement for finance lease (IFRS 16)')
    initial_recognition_move_count = fields.Integer(string='Initial Entry Count', compute='_compute_initial_recognition_move_count')

    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company.id)

    @api.depends('initial_recognition_move_id')
    def _compute_initial_recognition_move_count(self):
        for record in self:
            record.initial_recognition_move_count = 1 if record.initial_recognition_move_id else 0

    def action_view_initial_recognition(self):
        """Open the initial recognition journal entry."""
        self.ensure_one()
        if not self.initial_recognition_move_id:
            raise UserError(_('No initial recognition entry found.'))
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.initial_recognition_move_id.id
        return action

    # Helpers
    def _cancel_and_reverse_move(self, move):
        """
        Properly handle cancellation of accounting entries:
        - Posted invoices/bills: Create credit/debit note (reverse entry)
        - Draft invoices/bills: Cancel and delete
        - Posted journal entries: Reverse entry
        """
        if not move:
            return
        
        if move.state == 'posted':
            # For posted invoices/bills, create reversal (credit/debit note)
            if move.move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
                # Create reversal move
                reverse_moves = move._reverse_moves([{
                    'date': fields.Date.today(),
                    'ref': _('Reversal of %s - Contract Cancelled') % move.name,
                }])
                if reverse_moves:
                    reverse_moves.action_post()
            else:
                # For journal entries, create reverse entry
                move.button_reverse()
        else:
            # Draft entries can be cancelled and deleted directly
            if move.state == 'draft':
                move.button_cancel() if hasattr(move, 'button_cancel') else None
            move.unlink()

    def action_confirm(self):
        """Confirm lease contract and create initial journal entry for finance lease."""
        for record in self:
            if record.lease_type == 'finance':
                # For Finance Lease: Create IFRS 16 Commencement Entry
                record.action_confirm_finance_lease()
            record.state = 'running'
            if record.asset_id:
                record.asset_id.write({
                    'is_leased': True,
                    'lease_contract_id': record.id,
                })

    def action_cancel(self):
        for record in self:
            record.state = 'closed'
            # Cancel operating lease invoices
            for line in record.operating_payment_line_ids:
                record._cancel_and_reverse_move(line.invoice_id)
                line.invoice_id = False
            # Cancel finance lease invoices
            for line in record.payment_line_ids:
                record._cancel_and_reverse_move(line.invoice_id)
                line.invoice_id = False
            # Cancel initial recognition entry
            if record.initial_recognition_move_id:
                record._cancel_and_reverse_move(record.initial_recognition_move_id)
                record.initial_recognition_move_id = False
            if record.asset_id:
                record.asset_id.write({
                    'is_leased': False,
                    'lease_contract_id': False,
                })

    def action_reset_to_draft(self):
        for record in self:
            # Reuse cancel cleanup
            record.action_cancel()
            # Remove schedules to allow fresh regeneration
            record.operating_payment_line_ids.unlink()
            record.payment_line_ids.unlink()
            record.state = 'draft'

    @api.depends('date_start', 'date_end')
    def _compute_lease_term_years(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = relativedelta(record.date_end, record.date_start)
                record.lease_term_years = delta.years + (1 if delta.months or delta.days else 0)
            else:
                record.lease_term_years = 0

    @api.depends('asset_id')
    def _compute_asset_book_value(self):
        for record in self:
            if record.asset_id:
                # Get current book value from asset (Original - Accumulated Depreciation)
                # Try book_value first, then fallback to manual calculation
                book_value = getattr(record.asset_id, 'book_value', None)
                if book_value is not None:
                    record.asset_book_value = book_value
                else:
                    # Calculate: original_value - total accumulated depreciation
                    total_depreciation = sum(record.asset_id.depreciation_move_ids.filtered(lambda m: m.state == 'posted').mapped('amount_total'))
                    record.asset_book_value = record.asset_id.original_value - total_depreciation
            else:
                record.asset_book_value = 0.0

    @api.depends('asset_id')
    def _compute_asset_accounts(self):
        for record in self:
            if record.asset_id and record.asset_id.account_asset_id:
                record.account_fixed_asset_id = record.asset_id.account_asset_id.id
            else:
                record.account_fixed_asset_id = False

    @api.depends('total_lease_payments', 'discount_rate', 'date_start', 'date_end', 'payment_frequency')
    def _compute_present_value(self):
        for record in self:
            pv = 0.0
            if not record.total_lease_payments or not record.date_start or not record.date_end:
                record.present_value = pv
                continue
            delta = relativedelta(record.date_end, record.date_start)
            if record.payment_frequency == 'annual':
                num_periods = delta.years + (1 if delta.months > 0 or delta.days > 0 else 0)
                rate_per_period = (record.discount_rate or 0.0) / 100.0
            else:
                num_periods = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
                rate_per_period = ((record.discount_rate or 0.0) / 100.0) / 12.0

            if num_periods <= 0:
                record.present_value = 0.0
                continue

            payment_per_period = record.total_lease_payments / num_periods
            if rate_per_period == 0:
                pv = payment_per_period * num_periods
            else:
                pv = payment_per_period * ((1 - (1 + rate_per_period) ** (-num_periods)) / rate_per_period)
            record.present_value = pv

    @api.depends('total_lease_payments', 'present_value')
    def _compute_deferred_interest(self):
        for record in self:
            if record.total_lease_payments and record.present_value:
                record.deferred_interest_total = record.total_lease_payments - record.present_value
            else:
                record.deferred_interest_total = 0.0

    def action_compute_schedule(self):
        """Generate amortization schedule for finance lease."""
        for record in self:
            if record.lease_type != 'finance':
                continue
            if not record.present_value or not record.total_lease_payments or not record.discount_rate:
                raise UserError(_('Please fill Present Value, Total Lease Payments, and Discount Rate.'))
            record.payment_line_ids.unlink()

            opening = record.present_value
            rate_annual = record.discount_rate / 100.0

            # Determine periods and payment amount per period
            if record.payment_frequency == 'annual':
                delta = relativedelta(record.date_end, record.date_start)
                num_periods = delta.years + (1 if delta.months > 0 or delta.days > 0 else 0)
                period_delta = relativedelta(years=1)
                rate_per_period = rate_annual
                first_payment_date = record.date_start.replace(month=12, day=31)
                if first_payment_date <= record.date_start:
                    first_payment_date = first_payment_date + relativedelta(years=1)
            else:  # monthly
                delta = relativedelta(record.date_end, record.date_start)
                num_periods = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
                period_delta = relativedelta(months=1)
                rate_per_period = rate_annual / 12.0
                first_payment_date = record.date_start + relativedelta(months=1, day=1) + relativedelta(days=-1)

            payment_per_period = (record.total_lease_payments / num_periods) if num_periods else 0.0
            payment_date = first_payment_date

            lines = []
            for i in range(num_periods):
                interest = opening * rate_per_period
                principal = payment_per_period - interest
                closing = opening - principal
                if closing < 0:
                    principal = opening
                    interest = payment_per_period - principal
                    closing = 0.0
                lines.append((0, 0, {
                    'year_index': i + 1,
                    'payment_date': payment_date,
                    'opening_receivable': opening,
                    'interest_amount': interest,
                    'principal_amount': principal,
                    'total_payment': payment_per_period,
                    'closing_receivable': closing,
                }))
                opening = closing
                payment_date = payment_date + period_delta
            record.payment_line_ids = lines

    def action_confirm_finance_lease(self):
        """
        IFRS 16 Commencement Entry for Finance Lease (Lessor):
        Dr Lease Receivable (PV)
           Cr Fixed Asset (Book Value)
           Cr Selling Profit (if PV > BV)
        OR Dr Selling Loss (if BV > PV)
        
        No Deferred Interest in initial entry per IFRS 16.
        Interest is recognized over time when payments are received.
        """
        for record in self:
            if record.lease_type != 'finance':
                continue
            if not record.present_value or not record.asset_book_value:
                raise UserError(_('Please fill Present Value and Asset Book Value.'))
            if not record.account_lease_receivable_id or not record.account_fixed_asset_id:
                raise UserError(_('Please configure Lease Receivable and Fixed Asset accounts.'))
            
            # Calculate Selling Profit/Loss per IFRS 16
            selling_profit_loss = record.present_value - record.asset_book_value
            
            line_ids = [
                (0, 0, {
                    'name': _('Net Investment in Lease (Lease Receivable)'),
                    'account_id': record.account_lease_receivable_id.id,
                    'debit': record.present_value,
                    'credit': 0.0,
                    'partner_id': record.lessee_id.id,
                }),
                (0, 0, {
                    'name': _('Derecognition of Underlying Asset'),
                    'account_id': record.account_fixed_asset_id.id,
                    'debit': 0.0,
                    'credit': record.asset_book_value,
                    'partner_id': record.lessee_id.id,
                }),
            ]
            
            # Add Selling Profit or Loss line
            if abs(selling_profit_loss) > 0.01:
                if not record.account_selling_profit_id:
                    raise UserError(_('Please configure Selling Profit/Loss Account for the gain/loss on lease commencement.'))
                line_ids.append((0, 0, {
                    'name': _('Selling Profit on Finance Lease') if selling_profit_loss > 0 else _('Selling Loss on Finance Lease'),
                    'account_id': record.account_selling_profit_id.id,
                    'debit': 0.0 if selling_profit_loss > 0 else abs(selling_profit_loss),
                    'credit': selling_profit_loss if selling_profit_loss > 0 else 0.0,
                    'partner_id': record.lessee_id.id,
                }))
            
            move_vals = {
                'date': record.date_start,
                'ref': _('%s - Finance Lease Commencement') % record.name,
                'journal_id': record.journal_lease_id.id,
                'line_ids': line_ids,
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            record.initial_recognition_move_id = move.id
            
            # Mark asset as leased
            record.asset_id.write({
                'is_leased': True,
                'lease_contract_id': record.id,
            })

    def action_create_operating_invoice(self):
        """Generate operating lease payment schedule based on frequency."""
        self.ensure_one()
        if self.lease_type != 'operating':
            raise UserError(_('This action is only for Operating Lease.'))
        if not self.operating_payment_amount:
            raise UserError(_('Please set Operating Lease Payment Amount.'))
        if not self.account_rental_income_id:
            raise UserError(_('Please configure Rental Income Account.'))
        
        # Mark asset as leased
        self.asset_id.write({
            'is_leased': True,
            'lease_contract_id': self.id,
        })
        
        # Delete existing payment lines
        self.operating_payment_line_ids.unlink()
        
        # Generate payment schedule
        payment_date = self.date_start
        lines = []
        payment_index = 1
        
        if self.payment_frequency == 'annual':
            period_delta = relativedelta(years=1)
        else:  # monthly
            period_delta = relativedelta(months=1)
        
        # Generate payments until date_end
        while payment_date <= self.date_end:
            lines.append((0, 0, {
                'payment_index': payment_index,
                'payment_date': payment_date,
                'payment_amount': self.operating_payment_amount,
            }))
            payment_date = payment_date + period_delta
            payment_index += 1
        
        self.operating_payment_line_ids = lines
        return True

    def action_create_finance_invoices(self):
        """Create invoices for all payment lines without invoice."""
        self.ensure_one()
        if self.lease_type != 'finance':
            raise UserError(_('This action is only for Finance Lease.'))
        for line in self.payment_line_ids.filtered(lambda l: not l.invoice_id):
            line.action_create_customer_invoice()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lease.lessor.contract') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.ensure_one()
        self.state = 'pending'
