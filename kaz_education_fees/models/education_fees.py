# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class EducationFees(models.Model):
    """
    Model: Education Fees

    This model manages the process of requesting, validating, and reimbursing education-related fees
    (such as tuition, books, transport, and other expenses) for eligible employees' children.
    It enforces eligibility rules, financial limits, and multi-stage approval workflows.

    Main Features:
    --------------
    - Linked to employee, child, school, contract, academic year/grade/semester.
    - Tracks multiple expense categories per request.
    - Computes remaining allowance per employee and per child dynamically.
    - Defines and enforces maximum eligible children based on employee type (local/expat).
    - Ensures expense amount is within both child and reimbursement limits.
    - Supports HR team and HR manager level approvals.
    - Requires attachments for validation.
    - Includes activity scheduling and approval notifications by group.
    - Prevents duplicate claims for the same child in a single academic year.
    - Integrated with chatter, activity mixin, and email notifications.

    Key Fields:
    -----------
    - `employee_id`: The employee submitting the request.
    - `kid_id`: The child for whom the reimbursement is requested.
    - `contract_id`: Computed current running contract of the employee.
    - `academic_year_id`: School year to which the request applies.
    - `supporting_document_ids`: Required supporting documents for the claim.
    - `amount_paid`: Computed sum of tuition, book, transport, and other fees.
    - `remaining_allowance_amount`: Minimum between employee-level and child-level remaining cap.
    - `state`: Workflow status (draft → HR Team → HR Manager → Approved/Refused/Cancelled).
    - `seq`: Sequence number for identification.
    - `is_eligible`: Eligibility of the claim, computed externally.

    Business Rules & Validations:
    -----------------------------
    - Employee must have an open contract.
    - Expense amount must be > 0 and within individual and global limits.
    - One reimbursement per child per academic year.
    - Record can be reset to draft only from 'cancel'.
    - Record can only be deleted if it's in 'draft' or 'cancel' state.
    - Refusal requires reason and notification.
    - Maximum number of children allowed: 4 (locals), 3 (expats).

    Workflow:
    ---------
    1. Draft: Employee submits a new request.
    2. HR Team: First approval level.
    3. HR Manager: Final approval level.
    4. Confirmed: Approved and ready for reimbursement.
    5. Refused: Sent back with rejection reason.
    6. Cancelled: User withdrawn or system rejected.

    Notifications:
    --------------
    - Approval activities are scheduled only for users *not* in higher groups.
    - Group hierarchy is enforced to avoid redundant notifications.

    Dependencies:
    -------------
    - `hr.employee`, `kids.details`, `academic.year`, `res.school`, `hr.contract`
    - Sequence: `education.fees.seq`
    """

    _name = 'education.fees'
    _description = 'Education Fees'
    _rec_name = 'employee_id'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_default_employee(self):
        """
            Return the employee record linked to the current user and company.
            Used to default `employee_id` on record creation.
            """
        emp = self.env['hr.employee'].sudo().search([(
            'user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)], limit=1)
        return emp.id

    employee_id = fields.Many2one(string='Employee',
                                  comodel_name='hr.employee',
                                  required=True,
                                  default=get_default_employee,
                                  domain="[('grade_id.is_education_allowance', '=', True)]",
                                  tracking=True)
    grade_id = fields.Many2one('hr.grade',
                               related="employee_id.grade_id")
    contract_id = fields.Many2one(string='Contract',
                                  comodel_name='hr.contract',
                                  compute='_compute_contract',
                                  tracking=True)
    kaz_employee_type = fields.Selection(related="employee_id.kaz_employee_type")
    seq = fields.Char(default='New', readonly=True, tracking=True)
    hire_date = fields.Date(string='Hire Date', related="employee_id.hire_date",
                            tracking=True)

    max_child_eligible = fields.Integer(string='Max Child Eligible',
                                        compute='compute_max_child_eligible',
                                        tracking=True)
    payslip_id = fields.Many2one('hr.payslip', string='Education Payslip', copy=False)

    def action_open_related_payroll(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip'),
            'view_mode': 'form',
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'views': [[False, 'form']],
        }

    @api.depends('employee_id')
    def compute_max_child_eligible(self):
        """
                Compute the maximum number of children eligible for education fees
                based on employee type (local or expat).
                """
        for rec in self:
            if rec.employee_id.kaz_employee_type == 'local':
                rec.max_child_eligible = 4
            elif rec.employee_id.kaz_employee_type == 'expat':
                rec.max_child_eligible = 3
            else:
                rec.max_child_eligible = 0

    supporting_document_ids = fields.One2many('supporting.documents.fees',
                                              'education_fees_id',
                                              string='Supporting document',
                                              tracking=True, required=True)

    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
    school_name = fields.Many2one('res.school', string='School Name', tracking=True)
    date = fields.Date("Date", required=True, default=fields.Date.today())
    year = fields.Char(compute='calc_year')

    def action_reset(self):
        """
               Reset the record to draft state only if it's currently cancelled.
               Also clears any scheduled activities.
               """
        for rec in self:
            if rec.state != 'cancel':
                raise ValidationError(
                    'Only canceled Education Fee requests can be '
                    'reset to Draft.')
            rec.activity_ids.unlink()
            rec.write({
                'state': 'draft'
            })

    @api.depends('date')
    def calc_year(self):
        """
                Compute the calendar year from the request date.
                Used in filtering and grouping.
                """
        for rec in self:
            rec.year = rec.date.year

    paid = fields.Boolean(copy=False, string="Paid")

    child_allowance_amount = fields.Monetary(string='Maximum allowance amount per child',
                                             currency_field='currency_id',
                                             related='grade_id.per_child_allowance',
                                             readonly=True)
    reimburse_allowance_amount = fields.Monetary(string='Maximum reimburse amount limit',
                                                 currency_field='currency_id',
                                                 related='grade_id.reimbursement_limit', )
    amount_paid = fields.Monetary(string='Amount to pay', tracking=True, compute='_compute_amount_paid',
                                  currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_team', 'HR Team'),
        ('hr_manager', 'HR Manager'),
        ('confirmed', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Cancel'),
    ],
        default='draft',
        copy=False,
        tracking=True)
    kid_id = fields.Many2one('kids.details', string='Child')
    academic_year_id = fields.Many2one(string='Academic year',
                                       comodel_name='academic.year',
                                       tracking=True)
    academic_semester = fields.Selection(string='Academic Semester',
                                         selection=[('1', '1'), ('2', '2'), ('3', '3')],
                                         tracking=True)
    academic_grade_id = fields.Many2one(string='Academic Grade',
                                        comodel_name='academic.grade', tracking=True)
    dob = fields.Date(related='kid_id.age', string="DOB")
    school_id = fields.Many2one('res.school', string="school")
    country_id = fields.Many2one('res.country',
                                 related="school_id.country_id",
                                 string="Country")
    state_id = fields.Many2one(related="school_id.state_id", string="City")
    is_eligible = fields.Boolean(string='Eligible')
    remaining_allowance_amount = fields.Monetary(string='Remaining Allowance Amount',
                                                 compute='_compute_remaining_allowance_amount',
                                                 currency_field='currency_id')
    book_fees = fields.Monetary(currency_field='currency_id')
    transportation_fees = fields.Monetary(currency_field='currency_id')
    tuition_fees = fields.Monetary(currency_field='currency_id')
    other_fees = fields.Monetary(currency_field='currency_id')
    refuse_reason_ids = fields.One2many('refuse.reason', 'education_fees_id')

    @api.depends('book_fees', 'transportation_fees', 'tuition_fees', 'other_fees')
    def _compute_amount_paid(self):
        """
                Calculate total amount to pay based on all entered fee fields.
                """
        for rec in self:
            amounts = [rec.book_fees, rec.transportation_fees, rec.tuition_fees, rec.other_fees]
            rec.amount_paid = sum(amounts)

    def _check_child_eligible(self):
        """
                Check that the number of children submitted for education fees
                by the employee within the same academic year does not exceed the
                allowable maximum. Raise error if exceeded.
                """
        domain = [
            ('academic_year_id', '=', self.academic_year_id.id),
            ('employee_id', '=', self.employee_id.id),
            ('state', 'not in', ['draft', 'refuse', 'cancel'])
        ]

        if isinstance(self.id, int):
            domain.append(('id', '!=', self.id))

        existing_requests = self.search(domain)
        unique_kids = set(existing_requests.mapped('kid_id.id'))

        # Include current kid in the count
        unique_kids.add(self.kid_id.id)

        if len(unique_kids) > self.max_child_eligible:
            raise UserError(
                f"The number of eligible children exceeds the allowed limit of {self.max_child_eligible} "
                f"for {self.employee_id.name} in the academic year {self.academic_year_id.name}."
            )

    @api.depends('kid_id', 'academic_year_id')
    def _compute_remaining_allowance_amount(self):
        """
                Compute the remaining amount eligible for reimbursement for the selected
                child and employee in the current academic year.
                """
        for rec in self:
            if not rec.kid_id:
                rec.remaining_allowance_amount = 0.0
                continue

            if not (rec.kid_id and rec.academic_year_id and rec.employee_id):
                rec.remaining_allowance_amount = rec.child_allowance_amount
                continue

            domain_base = [
                ('academic_year_id', '=', rec.academic_year_id.id),
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'not in', ['draft', 'refuse', 'cancel'])
            ]
            #
            if isinstance(rec.id, int):
                domain_base.append(('id', '!=', rec.id))

            # All fees for employee in the academic year (for reimburse limit)
            employee_fees = self.search(domain_base)

            # All fees for the same kid and year (for child limit)
            child_fees = employee_fees.filtered(lambda x: x.kid_id.id == rec.kid_id.id)

            # Sum of already paid amounts
            total_paid_employee = sum(employee_fees.mapped('amount_paid'))
            total_paid_child = sum(child_fees.mapped('amount_paid'))

            # Calculate how much is remaining from both constraints
            remaining_per_employee = rec.reimburse_allowance_amount - total_paid_employee
            remaining_per_child = rec.child_allowance_amount - total_paid_child

            # Final remaining is the minimum of the two
            rec.remaining_allowance_amount = min(remaining_per_employee, remaining_per_child)

    def send_notify2_group(self, group_xml_id):
        """
                Notify only users in the target group (excluding higher-level roles)
                via scheduled activity requesting approval.
                """
        group = self.env.ref(group_xml_id)
        all_users = self.env['res.users'].search([('groups_id', 'in', group.id)])

        # Define group hierarchy (from lowest to highest)
        hierarchy = [
            'kaz_education_fees.group_base_user',
            'kaz_education_fees.group_hr_team',
            'kaz_education_fees.group_hr_manager',
        ]

        # Get index of current group
        current_index = hierarchy.index(group_xml_id)

        # Get all higher-level groups
        higher_groups = hierarchy[current_index + 1:]

        # Get all users from higher-level groups
        higher_users = self.env['res.users']
        for high_group_id in higher_groups:
            high_group = self.env.ref(high_group_id)
            higher_users |= self.env['res.users'].search([('groups_id', 'in', high_group.id)])

        # Exclude higher-level users from current group users
        target_users = all_users - higher_users
        for user in target_users:
            self.activity_schedule(
                act_type_xmlid='kaz_education_fees.mail_activity_send_note2_approve',
                note='Please Approve',
                user_id=user.id
            )

    def action_refuse(self):
        """
                Open a wizard form to input the reason for refusal of education fee.
                """
        return {
            "type": "ir.actions.act_window",
            "res_model": "refuse.reason",
            "context": {
                'default_education_fees_id': self.id,
                'field_name': 'education_fees_id',
                'state_field': 'state',
                'state_value': 'refuse',
                'refusal_template_id': 'kaz_education_fees.email_template_refusal_notification_education_fees',

            },
            "name": _("Refuse Reason"),
            'view_mode': 'form',
            "target": "new",
        }

    def _validate_before_send(self):
        """
        Perform pre-validation checks before progressing the record.

        This method checks:
        - Total amount paid must be greater than zero and within limits.
        - At least one supporting document is attached.
        - Number of eligible children does not exceed the allowed maximum.
        """
        self._check_total_pay()
        self._check_attachments()
        self._check_child_eligible()

    def send_to_hr_team(self):
        """
        Submit the request to the HR Team for review.

        Performs validation, then updates the state to 'hr_team' and
        notifies users in the HR Team group, excluding higher groups.
        """
        self._validate_before_send()
        self.write({'state': 'hr_team'})
        self.send_notify2_group('kaz_education_fees.group_hr_team')

    def send_to_hr_manager(self):
        """
        Forward the request from HR Team to the HR Manager for approval.

        Updates the state to 'hr_manager' and sends a notification
        to users in the HR Manager group, excluding higher levels.
        """
        self.write({'state': 'hr_manager'})
        self.send_notify2_group('kaz_education_fees.group_hr_manager')

    def btn_confirm(self):
        """
        Confirm and finalize the request.

        Sets the record's state to 'confirmed'.
        """
        for edu in self:
            edu.state = 'confirmed'

    def btn_cancel(self):
        """
        Cancel the request.

        Changes the state to 'cancel' without deleting the record.
        """
        for edu in self:
            edu.state = 'cancel'

    def reset_draft(self):
        """
        Reset the request back to draft.

        Typically used after cancellation to allow editing and re-submission.
        """
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to assign a sequence number.

        :param vals: Dictionary of values for the new record.
        :return: The newly created record.
        """
        for vals in vals_list:
            vals['seq'] = self.env['ir.sequence'].next_by_code('education.fees.seq')
        return super(EducationFees, self).create(vals_list)

    @api.depends('employee_id')
    def _compute_contract(self):
        """
        Compute the current running contract of the employee.

        Fetches the latest open contract by descending start date.
        """
        for edu in self:
            contract = self.env['hr.contract'].sudo().search(
                [('employee_id', '=', edu.employee_id.id),
                 ('state', '=', 'open')],
                limit=1, order='date_start DESC'
            )
            edu.contract_id = contract.id if contract else False

    def unlink(self):
        """
        Restrict deletion to draft or cancelled records only.

        :raises UserError: If the record is not in draft or cancel state.
        :return: True if deletion succeeds.
        """
        for record in self:
            if record.state not in ('draft', 'cancel'):
                raise UserError(
                    'You cannot delete an Education Fee which is not in draft or cancelled state.'
                )
        return super(EducationFees, self).unlink()

    @api.constrains('employee_id')
    def check_running_contract(self):
        """
        Ensure the employee has a running contract.

        :raises ValidationError: If no open contract is found.
        """
        for edu in self:
            if not edu.contract_id:
                raise ValidationError(
                    _("This employee does not have a running contract."))

    def _check_total_pay(self):
        """
        Validate that the total amount paid is positive and within the limits.

        :raises UserError: If the amount is zero, exceeds the per-child limit,
                           or the remaining reimbursement limit.
        """
        if self.amount_paid <= 0:
            raise UserError(
                "The total amount paid must be greater than zero before submission. "
                "Please ensure that values are entered for book, transport, tuition, or other fees."
            )

        if self.amount_paid > self.child_allowance_amount:
            raise UserError(
                f"The amount to be paid {self.amount_paid} exceeds the allowed limit per child "
                f"{self.child_allowance_amount}. Please adjust the amount accordingly."
            )

        if self.amount_paid > self.remaining_allowance_amount:
            raise UserError(
                f"The amount to be paid {self.amount_paid} exceeds the remaining allowable reimbursement "
                f"{self.remaining_allowance_amount} for this academic year. Please adjust the amount accordingly."
            )

    def _check_attachments(self):
        """
        Ensure at least one supporting document is attached.

        :raises UserError: If no documents are found.
        """
        if not self.supporting_document_ids:
            raise UserError(
                "Please attach at least one supporting document before submitting this request to HR.")

    def get_record_url(self):
        """
        Generate a direct URL to open this record in the web interface.

        :return: A string URL pointing to the form view of the current record.
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        return f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"
