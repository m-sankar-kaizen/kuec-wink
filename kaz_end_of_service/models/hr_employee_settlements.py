# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrEmployeeSettlements(models.Model):
    """
    Model: hr.employee.settlements

    This model handles the end-of-service settlement
     process for employees. It allows HR officers to
    calculate and track the various components of a
     final settlement, such as basic salary, cost of living
    allowance, vacation allowance, gratuity, pension,
     and leave encashment. It also manages the workflow
    from draft to approval and integrates with payroll
     and accounting modules.

    Key Features:
    - Tracks employment period and type of separation
    - Calculates various allowances based on employee contract and type
    - Generates payslips with custom structure for end-of-service
    - Records final accounting move and integrates with salary journal
    - Tracks approval workflow for settlement confirmation
    """
    _name = 'hr.employee.settlements'
    _description = 'Employee Settlements'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Info
    name = fields.Char(readonly=True, copy=False, default=lambda x: _('New'))
    employee_id = fields.Many2one('hr.employee', required=True)
    kaz_employee_type = fields.Selection(
        related='employee_id.kaz_employee_type')
    department_id = fields.Many2one('hr.department',
                                    related="employee_id.department_id")
    job_id = fields.Many2one('hr.job', related="employee_id.job_id")
    # Dates
    relieving_date = fields.Date(required=True)
    joined_date = fields.Date(related='employee_id.hire_date')
    current_month_first_date = fields.Date(string="Start Date (Current Month)",
                                           compute='compute_last_month_start_date')
    last_working_date = fields.Date(required=True)
    request_date = fields.Date(default=fields.Date.today(), required=True)
    # Work Duration
    years_worked = fields.Float(compute='_compute_worked_years', store=True)
    days_worked = fields.Float(compute='_compute_worked_days', store=True)
    settlement_computed = fields.Boolean(default=False)
    # Workflow State
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('cancel', 'Cancel'),
        ('rejected', 'Rejected')
    ], default='draft', copy=False, tracking=True)

    type_of_separation = fields.Selection(selection=[
        ('resignation', 'Resignation'),
        ('terminate', 'Terminate'),
        ('retirement', 'Retirement')
    ], default='resignation')

    # Contract & Payroll
    current_contract_id = fields.Many2one('hr.contract',
                                          compute='_compute_contract',
                                          store=True, tracking=True)
    journal_id = fields.Many2one('account.journal', 'Salary Journal',
                                 related="payroll_structure_id.journal_id")
    payroll_structure_id = fields.Many2one('hr.payroll.structure',
                                           domain="[('is_end_of_service', '=', True)]",
                                           default=lambda self: self.env.ref(
                                               'kaz_end_of_service.end_of_service_structure'),
                                           required=True)
    end_of_service_payslip = fields.Many2one('hr.payslip',
                                             copy=False,
                                             readonly=True)
    date_account = fields.Date(related="end_of_service_payslip.date")
    move_id = fields.Many2one('account.move', 'Accounting Entry',
                              related="end_of_service_payslip.move_id",
                              copy=False)
    move_state = fields.Selection(related='move_id.state')
    # Contract Salary & Allowances
    basic_contract = fields.Float(string="Basic",
                                  related='current_contract_id.scale_basic')
    cost_of_living_contract = fields.Monetary(string="Cost of Living",
                                              related='current_contract_id.cost_of_living_subsidy',
                                              currency_field='currency_id')
    vacation_allowance_contract = fields.Monetary(string="Vacation Allowance",
                                                  related='current_contract_id.vacation_allowance',
                                                  currency_field='currency_id')
    housing_allowance = fields.Monetary(string="Housing Allowance",
                                        related='current_contract_id.l10n_ae_housing_allowance',
                                        currency_field='currency_id')
    child_allowance = fields.Monetary(string="Child Allowance",
                                      related='current_contract_id.child_allowance',
                                      currency_field='currency_id')
    social_allowance = fields.Monetary(currency_field='currency_id')
    shift_allowance = fields.Monetary(currency_field='currency_id')
    stipend_allowance = fields.Monetary(currency_field='currency_id')
    market_differential = fields.Monetary(currency_field='currency_id',
                                          related='current_contract_id.market_differential')
    other_allowance = fields.Monetary(currency_field='currency_id')
    national_allowance = fields.Monetary(currency_field='currency_id')
    supplemental_allowance = fields.Monetary(currency_field='currency_id')
    general_allowance = fields.Monetary(currency_field='currency_id')
    mobile_allowance = fields.Monetary(currency_field='currency_id')

    other_earnings = fields.Monetary(currency_field='currency_id')
    rounding = fields.Monetary(currency_field='currency_id',
                               related='current_contract_id.rounding')
    other_deductions = fields.Monetary(currency_field='currency_id')
    # Calculated Settlement Components
    basic = fields.Monetary('Basic', currency_field='currency_id', copy=False,
                            default=0.0, readonly=True)
    cols = fields.Monetary('Cost of Living Subsidy',
                           currency_field='currency_id', copy=False,
                           default=0.0, readonly=True)
    vacation_allowance = fields.Monetary('Vacation Allowance',
                                         currency_field='currency_id',
                                         copy=False, default=0.0, readonly=True)
    no_of_days = fields.Integer(string="No of Days", default=0, copy=False,
                                readonly=True)
    total = fields.Monetary(string='Total', currency_field='currency_id',
                            default=0.0, copy=False, readonly=True)
    other_earnings_settlement = fields.Monetary(string='Other Earnings',
                                                currency_field='currency_id',
                                                default=0.0, copy=False,
                                                readonly=True)
    other_deductions_settlement = fields.Monetary(string='Other Deductions',
                                                  currency_field='currency_id',
                                                  default=0.0, copy=False,
                                                  readonly=True)
    # Gratuity and Pension
    years = fields.Float(string="Years", default=0.0, copy=False, readonly=True)
    gratuity_amount = fields.Monetary(string="Total Gratuity",
                                      currency_field='currency_id', default=0.0,
                                      copy=False, readonly=True)
    pension_amount = fields.Monetary(string="Pension Amount",
                                     currency_field='currency_id', default=0.0,
                                     copy=False, readonly=True)

    balance_leave_this_annum = fields.Float('Balance Leave', copy=False)
    leave_balance_total = fields.Monetary(currency_field='currency_id',
                                          default=0.0, copy=False,
                                          readonly=True)

    total_payable = fields.Monetary(string='Total Payable',
                                    currency_field='currency_id', default=0.0,
                                    copy=False,
                                    compute='_compute_total_payable')
    # Company Info
    company_id = fields.Many2one('res.company', copy=False,
                                 readonly=True,
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')

    # Leave Balance
    @api.onchange('employee_id')
    def onchange_employee_id_leave(self):
        """Auto-fetch leave balance when employee is selected."""
        self.balance_leave_this_annum = self.employee_id.remaining_leaves

    @api.depends('total', 'gratuity_amount', 'leave_balance_total',
                 'pension_amount', 'other_earnings_settlement',
                 'other_deductions_settlement')
    def _compute_total_payable(self):
        """Calculate the final amount payable to employee."""
        for total in self:
            total.total_payable = total.total + total.gratuity_amount + total.leave_balance_total + total.other_earnings_settlement - total.pension_amount - total.other_deductions_settlement

    @api.model_create_multi
    def create(self, vals_list):
        """Assign unique sequence number upon creation."""
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.employee.settlements') or _('New')
        return super().create(vals_list)

    @api.depends('joined_date', 'last_working_date')
    def _compute_worked_years(self):
        """Calculate number of years worked based on join and last working date."""
        for rec in self:
            rec.years_worked = 0.0
            if rec.joined_date and rec.last_working_date:
                delta = relativedelta(rec.last_working_date, rec.joined_date)
                rec.years_worked = (
                        delta.years +
                        (delta.months / 12.0) +
                        (delta.days / 365.0)
                )

    @api.depends('joined_date', 'last_working_date')
    def _compute_worked_days(self):
        """Calculate total number of days worked."""
        for rec in self:
            if rec.last_working_date and rec.joined_date:
                no_of_days = (rec.last_working_date - rec.joined_date).days + 1
                rec.days_worked = no_of_days
            else:
                rec.days_worked = 0.0

    @api.depends('last_working_date')
    def compute_last_month_start_date(self):
        """Compute the first date of the month of the last working day."""
        for rec in self:
            if rec.last_working_date:
                rec.current_month_first_date = rec.last_working_date.replace(
                    day=1)
            else:
                rec.current_month_first_date = ''

    @api.depends('employee_id')
    def _compute_contract(self):
        """Fetch most recent open/closed contract for the employee."""
        for rec in self:
            contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ('open', 'close'))
            ], limit=1, order='date_start DESC')
            rec.current_contract_id = contract.id if contract else False

    def action_create_draft_entry(self):
        """Create draft end-of-service payslip based on current contract and settlement data."""
        for rec in self:
            if not rec.payroll_structure_id:
                raise ValidationError(_("Choose a Payroll Structure."))
            payslip = self.env['hr.payslip'].sudo().create({
                'employee_id': rec.employee_id.id,
                'contract_id': rec.current_contract_id.id,
                'date_from': rec.current_month_first_date,
                'date_to': rec.last_working_date,
                'struct_id': rec.payroll_structure_id.id,
                'end_of_service_id': rec.id,
                'name': 'End of Service - ' + rec.employee_id.name
            })
            rec.end_of_service_payslip = payslip.id
            payslip.compute_sheet()
            return {
                "type": "ir.actions.act_window",
                "res_model": "hr.payslip",
                "res_id": payslip.id,
                "view_mode": 'form',
                "target": "new",
            }

    def action_confirm(self):
        """Compute and confirm the settlement."""
        self.action_compute_settlement()
        self.write({'state': 'confirm'})

    def action_approve(self):
        """Approve the settlement."""
        self.write({'state': 'approved'})

    def action_cancel(self):
        """Cancel the settlement request."""
        self.write({'state': 'cancel'})

    def action_reject(self):
        """Reject the settlement request."""
        self.write({'state': 'rejected'})

    def action_reset(self):
        """Reset the settlement to draft and allow recomputation."""
        self.write({'state': 'draft', 'settlement_computed': False})

    def action_compute_settlement(self):
        """
        Perform detailed calculation of settlement components:
        - Basic, COLS, Vacation based on contract salary and days
        - Gratuity (for expats)
        - Pension (for locals)
        - Leave encashment
        - Copy other allowances
        """
        for rec in self:
            rec.basic = rec.cols = rec.vacation_allowance = rec.no_of_days = 0.0
            rec.total = rec.years = rec.gratuity_amount = rec.pension_amount = 0.0
            rec.leave_balance_total = 0.0
            if rec.current_contract_id.state not in ['open', 'close']:
                raise ValidationError(
                    _("The employee doesn't have a valid contract."))
            if not rec.relieving_date or not rec.joined_date:
                raise ValidationError(_("Choose relieve date and joined date."))

            rec.no_of_days = abs(
                rec.last_working_date - rec.current_month_first_date).days + 1

            first_date = rec.current_month_first_date
            next_month_first = first_date + relativedelta(months=1)
            last_day_of_month = next_month_first - relativedelta(days=1)
            days_in_month = last_day_of_month.day

            rec.basic = rec.current_contract_id.scale_basic / days_in_month * rec.no_of_days
            rec.cols = rec.current_contract_id.cost_of_living_subsidy / days_in_month * rec.no_of_days
            rec.vacation_allowance = rec.current_contract_id.vacation_allowance / days_in_month * rec.no_of_days
            rec.total = rec.basic + rec.cols + rec.vacation_allowance

            if rec.kaz_employee_type == 'expat':
                rec.years = rec.years_worked
                rec.gratuity_amount = rec.basic_contract / 365 * rec.days_worked if rec.years >= 1 else 0.0
            elif rec.kaz_employee_type == 'local':
                rec.pension_amount = rec.current_contract_id.pention_employee_contribution_uae / days_in_month * rec.no_of_days

            sum_basic_cols = rec.basic_contract + rec.cost_of_living_contract
            per_day_salary = (sum_basic_cols / 30) * (7 / 5)
            rec.leave_balance_total = per_day_salary * rec.balance_leave_this_annum
            rec.other_earnings_settlement = rec.other_earnings
            rec.other_deductions_settlement = rec.other_deductions
            rec.settlement_computed = True
