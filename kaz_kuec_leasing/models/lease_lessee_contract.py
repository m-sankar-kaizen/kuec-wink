# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class LeaseLesseeContract(models.Model):
    _name = 'lease.lessee.contract'
    _description = 'Lessee Lease Contract (IFRS 16)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, name desc'

    # ========== CONTRACT DETAILS ==========
    name = fields.Char(
        string='Contract Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        tracking=True
    )
    
    asset_description = fields.Char(
        string='Asset',
        required=True,
        tracking=True,
        help='Description of the leased asset (e.g., Office Space, Equipment)'
    )
    
    lessor_id = fields.Many2one(
        'res.partner',
        string='Lessor',
        required=True,
        tracking=True,
        help='The lessor (landlord/supplier) from whom the asset is leased'
    )
    
    date_start = fields.Date(
        string='Lease Start Date',
        required=True,
        tracking=True,
        help='The commencement date of the lease'
    )
    
    date_end = fields.Date(
        string='Lease End Date',
        required=True,
        tracking=True,
        help='The end date of the lease term'
    )
    
    lease_term_years = fields.Integer(
        string='Lease Term (Years)',
        compute='_compute_lease_term_years',
        store=True,
        help='Lease term calculated from start and end dates'
    )
    
    payment_frequency = fields.Selection([
        ('annual', 'Annually'),
        ('quarterly', 'Quarterly'),
        ('monthly', 'Monthly'),
    ], string='Invoice Frequency', required=True, default='annual', tracking=True,
        help='How often vendor bills/invoices are generated: Annual (1/year), Quarterly (4/year), Monthly (12/year)')
    
    invoice_reminder_days = fields.Integer(
        string='Invoice Reminder (Days)',
        default=lambda self: self.env.company.lease_invoice_reminder_days or 7,
        help='Number of days before invoice due date to send reminder to Invoicing team'
    )
    
    payment_amount = fields.Monetary(
        string='Lease Payment Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
        help='The periodic lease payment amount (per frequency: annual, quarterly, or monthly). The system will annualize this automatically for PV calculations.'
    )
    
    discount_rate = fields.Float(
        string='Discount Rate (%)',
        required=True,
        digits=(16, 2),
        default=5.0,
        tracking=True,
        help='The incremental borrowing rate used to discount lease payments'
    )
    
    present_value = fields.Monetary(
        string='Present Value of Lease Payments',
        compute='_compute_present_value',
        inverse='_inverse_present_value',
        store=True,
        currency_field='currency_id',
        tracking=True,
        help='''Present value calculated using IFRS 16 formula (editable):

PV is ALWAYS calculated annually: PV = Σ(Annual Payment / (1 + r)^n) for n=1 to N

Where:
- Annual Payment = payment_amount × frequency multiplier
  * Annual: payment_amount × 1
  * Quarterly: payment_amount × 4
  * Monthly: payment_amount × 12
- r = Annual discount rate (%)
- N = Lease term (years)

Example:
Monthly payment = 10,000, Discount Rate = 5%, Term = 4 years
Annual payment = 10,000 × 12 = 120,000
PV = 120,000/1.05 + 120,000/1.05² + 120,000/1.05³ + 120,000/1.05⁴'''
    )
    
    present_value_manual = fields.Monetary(
        string='Manual Present Value',
        currency_field='currency_id',
        help='Manually overridden present value'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('running', 'Running'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    
    # ========== DEPRECIATION DETAILS ==========
    useful_life_value = fields.Integer(
        string='Useful Life',
        required=True,
        default=5,
        help='The useful life of the ROU asset'
    )
    
    useful_life_unit = fields.Selection([
        ('years', 'Years'),
        ('months', 'Months'),
    ], string='Useful Life Unit', required=True, default='years')
    
    depreciation_method = fields.Selection([
        ('linear', 'Straight Line'),
        ('degressive', 'Declining'),
        ('degressive-linear', 'Declining then Straight'),
    ], string='Depreciation Method', required=True, default='linear')
    
    declining_factor = fields.Float(
        string='Declining Factor',
        default=30.0,
        digits=(5, 2),
        help='Percentage used for declining balance depreciation (typically 20-40%)'
    )
    
    asset_id = fields.Many2one(
        'account.asset',
        string='ROU Asset',
        readonly=True,
        copy=False,
        help='The Right-of-Use asset created for this lease'
    )
    
    # ========== TERMS AND CONDITIONS ==========
    terms_html = fields.Html(
        string='Terms and Conditions',
        help='Additional terms and conditions of the lease contract'
    )
    
    # ========== ACCOUNTING SETUP ==========
    account_rou_id = fields.Many2one(
        'account.account',
        string='Right-of-Use Asset Account',
        required=True,
        help='Account for recognizing the Right-of-Use asset'
    )
    
    account_lease_liability_id = fields.Many2one(
        'account.account',
        string='Lease Liability Account',
        required=True,
        help='Account for recognizing the lease liability'
    )
    
    account_interest_expense_id = fields.Many2one(
        'account.account',
        string='Interest Expense Account',
        required=True,
        help='Account for recording interest expense on lease liability'
    )
    
    account_dep_expense_id = fields.Many2one(
        'account.account',
        string='Depreciation Expense Account',
        required=True,
        help='Account for recording depreciation expense'
    )
    
    account_dep_accum_id = fields.Many2one(
        'account.account',
        string='Accumulated Depreciation Account',
        required=True,
        help='Account for accumulated depreciation'
    )
    
    journal_dep_id = fields.Many2one(
        'account.journal',
        string='Depreciation Journal',
        required=True,
        domain=[('type', '=', 'general')],
        help='Journal for posting depreciation entries'
    )
    
    journal_rou_id = fields.Many2one(
        'account.journal',
        string='ROU Asset Entry Journal',
        required=True,
        domain=[('type', '=', 'general')],
        help='Journal for posting ROU asset and lease liability initial entries'
    )
    
    # ========== CHILD LINES ==========
    depreciation_line_ids = fields.One2many(
        'lease.lessee.depreciation.line',
        'contract_id',
        string='Depreciation Board',
        copy=False
    )
    
    payment_line_ids = fields.One2many(
        'lease.lessee.payment.line',
        'contract_id',
        string='Payment Board',
        copy=False
    )
    
    # ========== COMPUTED FIELDS ==========
    @api.depends('date_start', 'date_end')
    def _compute_lease_term_years(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = relativedelta(record.date_end, record.date_start)
                record.lease_term_years = delta.years + (1 if delta.months > 0 or delta.days > 0 else 0)
            else:
                record.lease_term_years = 0
    
    @api.depends('payment_amount', 'discount_rate', 'date_start', 'date_end', 'payment_frequency', 'present_value_manual')
    def _compute_present_value(self):
        for record in self:
            if record.present_value_manual:
                record.present_value = record.present_value_manual
            else:
                record.present_value = record._calculate_present_value()
    
    def _inverse_present_value(self):
        for record in self:
            record.present_value_manual = record.present_value
    
    @api.onchange('payment_amount', 'discount_rate', 'date_start', 'date_end', 'payment_frequency')
    def _onchange_pv_factors(self):
        """Reset manual override when any PV factor changes"""
        if self.present_value_manual and any([
            self.payment_amount,
            self.discount_rate,
            self.date_start,
            self.date_end,
            self.payment_frequency
        ]):
            self.present_value_manual = 0.0
    
    def _calculate_present_value(self):
        """Calculate Present Value using IFRS 16 formula - Always calculated annually"""
        self.ensure_one()
        
        if not self.payment_amount or not self.discount_rate or not self.date_start or not self.date_end:
            return 0.0
        
        rate = self.discount_rate / 100.0
        pv = 0.0
        
        # Calculate total annual payment based on invoice frequency
        if self.payment_frequency == 'annual':
            annual_payment = self.payment_amount
        elif self.payment_frequency == 'quarterly':
            annual_payment = self.payment_amount * 4
        else:  # monthly
            annual_payment = self.payment_amount * 12
        
        # Calculate number of years
        delta = relativedelta(self.date_end, self.date_start)
        num_years = delta.years + (1 if delta.months > 0 or delta.days > 0 else 0)
        
        # PV = sum of [annual_payment / (1 + r)^n] for n = 1 to N (Always Annual)
        for n in range(1, num_years + 1):
            pv += annual_payment / ((1 + rate) ** n)
        
        return pv
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start >= record.date_end:
                raise ValidationError(_('Lease End Date must be after Lease Start Date.'))
    
    @api.constrains('discount_rate')
    def _check_discount_rate(self):
        for record in self:
            if record.discount_rate <= 0:
                raise ValidationError(_('Discount Rate must be greater than zero.'))
    
    @api.constrains('payment_amount')
    def _check_payment_amount(self):
        for record in self:
            if record.payment_amount <= 0:
                raise ValidationError(_('Payment Amount must be greater than zero.'))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lease.lessee.contract') or 'New'
        return super().create(vals_list)
    
    def action_compute_schedules(self):
        """Compute depreciation and payment schedules before confirmation"""
        for record in self:
            record._generate_payment_schedule()
            record._sync_depreciation_from_asset()
    
    def action_confirm(self):
        """Confirm the lease contract and create initial accounting entries"""
        for record in self:
            if record.state not in ['draft', 'pending']:
                raise UserError(_('Only draft and pending contracts can be confirmed.'))

            # Generate payment schedule if not already done
            if not record.payment_line_ids:
                record._generate_payment_schedule()
            
            # Create the initial ROU asset and lease liability entry
            record._create_initial_entry()

            
            # Create the ROU asset
            record._create_rou_asset()
            
            # Sync depreciation from asset
            record._sync_depreciation_from_asset()
            
            record.state = 'running'
    
    def _create_initial_entry(self):
        """Create journal entry to recognize ROU asset and lease liability"""
        self.ensure_one()
        
        if not self.present_value:
            raise UserError(_('Present Value must be calculated before confirming the contract.'))
        
        move_vals = {
            'date': self.date_start,
            'ref': self.name,
            'journal_id': self.journal_rou_id.id,
            'line_ids': [
                (0, 0, {
                    'name': _('ROU Asset - %s') % self.asset_description,
                    'account_id': self.account_rou_id.id,
                    'debit': self.present_value,
                    'credit': 0.0,
                    'partner_id': self.lessor_id.id,
                }),
                (0, 0, {
                    'name': _('Lease Liability - %s') % self.asset_description,
                    'account_id': self.account_lease_liability_id.id,
                    'debit': 0.0,
                    'credit': self.present_value,
                    'partner_id': self.lessor_id.id,
                }),
            ],
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        self.message_post(
            body=_('Initial journal entry posted: ROU Asset and Lease Liability recognized for %s %s') % (
                self.currency_id.symbol, 
                '{:,.2f}'.format(self.present_value)
            )
        )
    
    def _create_rou_asset(self):
        """Create the Right-of-Use Asset"""
        self.ensure_one()
        
        # Determine method_period based on useful_life_unit
        if self.useful_life_unit == 'years':
            method_period = '12'  # Yearly depreciation
            method_number = self.useful_life_value
        else:
            method_period = '1'  # Monthly depreciation
            method_number = self.useful_life_value
        
        # Prepare asset values
        asset_vals = {
            'name': _('ROU Asset - %s') % self.asset_description,
            'original_value': self.present_value,
            'acquisition_date': self.date_start,
            'account_asset_id': self.account_rou_id.id,
            'account_depreciation_id': self.account_dep_accum_id.id,
            'account_depreciation_expense_id': self.account_dep_expense_id.id,
            'journal_id': self.journal_dep_id.id,
            'method': self.depreciation_method,  # Use method directly (already in correct format)
            'method_number': method_number,
            'method_period': method_period,
            'method_progress_factor': self.declining_factor / 100.0,  # Convert percentage to decimal
            'state': 'draft',
            'is_rou_asset': True,  # Mark as ROU Asset
            'lease_contract_id': self.id,  # Link to lease contract
        }
        
        asset = self.env['account.asset'].create(asset_vals)
        self.asset_id = asset.id
        
        # Validate the asset to generate depreciation lines
        asset.validate()
        
        self.message_post(
            body=_('ROU Asset created: %s') % asset.name
        )
    
    def _sync_depreciation_from_asset(self):
        """Sync depreciation schedule from the ROU asset"""
        self.ensure_one()
        
        # Clear existing lines
        self.depreciation_line_ids.unlink()
        
        if not self.asset_id:
            return
        
        # Get depreciation lines from asset
        asset_dep_lines = self.asset_id.depreciation_move_ids.sorted('date')
        
        accumulated = 0.0
        for move in asset_dep_lines:
            # Find the depreciation amount from move lines
            dep_amount = 0.0
            for line in move.line_ids:
                if line.account_id == self.account_dep_accum_id:
                    dep_amount = abs(line.credit - line.debit)
                    break
            
            accumulated += dep_amount
            remaining = self.present_value - accumulated
            
            self.env['lease.lessee.depreciation.line'].create({
                'contract_id': self.id,
                'date': move.date,
                'amount': dep_amount,
                'accumulated_amount': accumulated,
                'remaining_value': remaining if remaining > 0 else 0.0,
                'move_id': move.id,
            })
    
    def _generate_payment_schedule(self):
        """Generate payment schedule with principal and interest"""
        self.ensure_one()
        
        # Clear existing lines
        self.payment_line_ids.unlink()
        
        if not self.present_value or not self.payment_amount:
            return
        
        opening_liability = self.present_value
        rate = self.discount_rate / 100.0
        
        if self.payment_frequency == 'annual':
            delta = relativedelta(self.date_end, self.date_start)
            num_periods = delta.years + (1 if delta.months > 0 or delta.days > 0 else 0)
            period_delta = relativedelta(years=1)
            interest_rate = rate
            # First payment at end of first year (e.g., 31/12 if starting 01/01)
            payment_date = self.date_start.replace(day=31, month=12)
            if payment_date <= self.date_start:
                payment_date = payment_date + relativedelta(years=1)
        elif self.payment_frequency == 'quarterly':
            delta = relativedelta(self.date_end, self.date_start)
            num_periods = (delta.years * 4) + (delta.months // 3) + (1 if delta.months % 3 > 0 or delta.days > 0 else 0)
            period_delta = relativedelta(months=3)
            interest_rate = rate / 4.0
            # First payment at end of first quarter
            quarter_months = {1: 3, 2: 6, 3: 9, 4: 12}
            target_month = quarter_months[((self.date_start.month - 1) // 3) + 1]
            payment_date = self.date_start.replace(month=target_month, day=1) + relativedelta(days=-1)
            if payment_date <= self.date_start:
                payment_date = payment_date + relativedelta(months=3)
        else:  # monthly
            delta = relativedelta(self.date_end, self.date_start)
            num_periods = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
            period_delta = relativedelta(months=1)
            interest_rate = rate / 12.0
            # First payment at end of first month
            payment_date = self.date_start + relativedelta(months=1, day=1) + relativedelta(days=-1)
        
        for i in range(num_periods):
            # Calculate interest on opening liability
            interest = opening_liability * interest_rate
            
            # Principal is payment minus interest
            principal = self.payment_amount - interest
            
            # Closing liability
            closing_liability = opening_liability - principal
            
            # Ensure closing liability doesn't go negative
            if closing_liability < 0:
                principal = opening_liability
                interest = self.payment_amount - principal
                closing_liability = 0.0
            
            self.env['lease.lessee.payment.line'].create({
                'contract_id': self.id,
                'payment_date': payment_date,
                'opening_liability': opening_liability,
                'interest_amount': interest,
                'principal_amount': principal,
                'total_payment': self.payment_amount,
                'closing_liability': closing_liability,
            })
            
            # Move to next period
            opening_liability = closing_liability
            payment_date = payment_date + period_delta
    
    def action_cancel(self):
        """Cancel the contract, asset, and all related journal entries with proper reversals"""
        for record in self:
            if record.state == 'cancelled':
                continue
            
            # Cancel the asset if exists
            if record.asset_id:
                # Reverse posted depreciation moves, cancel draft ones
                for move in record.asset_id.depreciation_move_ids:
                    if move.state == 'posted':
                        # Create reversal entry for posted depreciation
                        move.button_reverse()
                    elif move.state == 'draft':
                        move.button_cancel()
                        move.unlink()
                
                # Set asset to cancel or draft
                if hasattr(record.asset_id, 'set_to_cancelled'):
                    record.asset_id.set_to_cancelled()
                else:
                    record.asset_id.write({'state': 'cancelled'})
            
            # Handle vendor bills: reverse posted bills, cancel draft bills
            for payment_line in record.payment_line_ids:
                if payment_line.vendor_bill_id:
                    bill = payment_line.vendor_bill_id
                    if bill.state == 'posted':
                        # Create debit note (reversal) for posted bills
                        reverse_moves = bill._reverse_moves([{
                            'date': fields.Date.today(),
                            'ref': _('Reversal of %s - Contract Cancelled') % bill.name,
                        }])
                        if reverse_moves:
                            reverse_moves.action_post()
                    elif bill.state == 'draft':
                        # Cancel and delete draft bills
                        bill.button_cancel()
                        bill.unlink()
            
            record.state = 'cancelled'
            record.message_post(body=_('Contract cancelled. Posted entries reversed with credit/debit notes, draft entries cancelled.'))
    
    def action_set_to_draft(self):
        """Reset to draft after cancellation"""
        for record in self:
            if record.state not in ['cancelled', 'running']:
                continue
            
            # Delete depreciation and payment lines to allow reconfiguration
            record.depreciation_line_ids.unlink()
            record.payment_line_ids.unlink()
            
            # Reset asset to draft if exists and was cancelled
            if record.asset_id:
                if record.asset_id.state in ['cancelled', 'close']:
                    record.asset_id.write({'state': 'draft'})
            
            record.state = 'draft'
            record.message_post(body=_('Contract reset to draft. Ready for reconfiguration.'))
    
    def action_view_rou_asset(self):
        """Open the ROU Asset form"""
        self.ensure_one()
        if not self.asset_id:
            raise UserError(_('No ROU Asset has been created yet.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('ROU Asset'),
            'res_model': 'account.asset',
            'res_id': self.asset_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(_('You cannot delete a confirmed lease contract.'))
        return super().unlink()
    
    @api.model
    def _cron_send_invoice_reminders(self):
        """Cron job to send invoice reminders and create vendor bills"""
        today = fields.Date.today()
        
        # Find all running contracts
        contracts = self.search([('state', '=', 'running')])
        
        for contract in contracts:
            for payment_line in contract.payment_line_ids:
                # Skip if bill already created
                if payment_line.vendor_bill_id:
                    continue
                
                # Check if we should send reminder
                reminder_date = payment_line.payment_date - relativedelta(days=contract.invoice_reminder_days)
                
                if today == reminder_date:
                    # Create activity for invoicing team
                    invoicing_group = self.env.ref('account.group_account_invoice', raise_if_not_found=False)
                    if invoicing_group:
                        users = invoicing_group.users
                        for user in users:
                            contract.activity_schedule(
                                'mail.mail_activity_data_todo',
                                date_deadline=payment_line.payment_date,
                                summary=_('Create Lease Invoice'),
                                note=_('Lease payment due on %s for contract %s.<br/>Amount: %s %s<br/>Please create vendor bill.') % (
                                    payment_line.payment_date,
                                    contract.name,
                                    contract.currency_id.symbol,
                                    '{:,.2f}'.format(payment_line.total_payment)
                                ),
                                user_id=user.id
                            )
                    
                    # Auto-create vendor bill
                    payment_line.action_create_vendor_bill()
                    
                    # Mark activity as done
                    activities = contract.activity_ids.filtered(
                        lambda a: a.date_deadline == payment_line.payment_date and a.activity_type_id.name == 'To Do'
                    )
                    activities.action_done()

    def action_submit(self):
        self.ensure_one()
        self.state = 'pending'
