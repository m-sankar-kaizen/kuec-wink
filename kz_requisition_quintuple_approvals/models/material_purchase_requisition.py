# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class MaterialPurchaseRequisition(models.Model):
    """
        Extends `material.purchase.requisition` to add:

        - Aggregated computation of budget amounts in currency.
        - Budget warning messages and over-budget detection per analytic account or expense account.
        - Auto-validation of analytic-account budgets after write.
        """
    _inherit = 'material.purchase.requisition'

    def _compute_show_approve(self):
        for requisition in self:
            if requisition.type:
                work_flow = requisition.get_groups_flow()
                if requisition.approvement_state == 'pending':
                    group_name = requisition.get_group_name(work_flow[0])
                    if requisition.env.user.has_group(group_name):
                        requisition.show_approve = True
                        return
                elif requisition.approvement_state not in ['draft', 'pending', 'approved',
                                                           'completed', 'rejected']:
                    if requisition.current_group:
                        old_index = work_flow.index(requisition.current_group)
                        new_index = old_index + 1
                        if new_index < len(work_flow):
                            group_name = requisition.get_group_name(work_flow[new_index])
                            if requisition.env.user.has_group(group_name):
                                requisition.show_approve = True
                                return
            requisition.show_approve = False

    amount_incurrency = fields.Float(
        string='Total Amount in Currency',
        required=False, compute='_compute_amount_incurrency', store=True)

    budget_warning_message = fields.Text(
        string="Budget Warning",
        required=False, compute='_compute_budget_warning_message')

    over_budget_text = fields.Text(
        string='Over_budget_ids', compute='_compute_budget_warning_message')
    purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='Purchase_ids',
        required=False, copy=False)

    approval_line_ids = fields.One2many('requisition.approval.line', 'requisition_id',
                                        string='Approval Lines')

    show_approve = fields.Boolean(
        string='Show Approve',
        required=False, compute="_compute_show_approve")

    department_ids = fields.Many2many(
        comodel_name='hr.department',
        string='Departments')
    attacchment_ids = fields.Many2many(
        'ir.attachment',
        'material_requisition_attachment_rel',
        'requisition_id',
        'attach_id',
        string='Scope of Work',
        required=False
    )
    shareholders_attacchment_ids = fields.Many2many(
        'ir.attachment',
        'material_requisition_shareholder_attachment_rel',
        'requisition_id',
        'attach_id',
        string='Shareholder Attach',
        required=False
    )
    board_attacchment_ids = fields.Many2many(
        'ir.attachment',
        'material_requisition_board_attachment_rel',
        'requisition_id',
        'attach_id',
        string='Board Attach',
        required=False
    )
    purchase_vendor_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Requisition Vendor',
        required=True)

    requisition_type = fields.Selection(
        selection=[
            ('purchase', 'Purchase Order'),
        ],
        string='Requisition Action',
        default='purchase',
        required=True,
    )
    type = fields.Selection(
        string='Type',
        selection=[('single_source', 'Single Source'),
                   ('standard', 'Standard'),
                   ('variation', 'Variation')],
    )

    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        required=False)

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase',
        required=False)

    replacement_requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string=' replacement_requisition_id',
        required=False, copy=False)

    resubmitted_requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string=' resubmitted_requisition_id',
        required=False, copy=False)

    resubmitted_original_requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string=' resubmitted_original_requisition_id',
        required=False, copy=False)

    original_requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string=' original_requisition_id',
        required=False, copy=False)

    approval_text = fields.Char(
        string='Approval',
        required=False)

    approvement_state = fields.Selection(
        string='Approval State',
        selection=[('draft', 'Draft'),
                   ('pending', 'Pending Approval'),
                   ('department_head_approval', 'Department Head Approved'),
                   ('budget_controller_approval', 'Budget Controller Approved'),
                   ('re_head_of_unit_approval', 'Head of Unit Approved'),
                   ('cfo_approval', 'CFO Approved'),
                   ('re_ceo_approval', 'CEO Approved'),
                   ('approved', 'Approved'),
                   ('completed', 'Completed'),
                   ('rejected', 'Rejected'),
                   ('cancel', 'Canceled'),
                   ],
        required=False, default='draft', copy=False, tracking=True)

    total_amount = fields.Float(
        string='Total Amount',
        store=True,
        required=False, compute='_compute_total_amount')

    current_group = fields.Char(
        string='Current_group',
        required=False, readonly=True, copy=False)

    po_count = fields.Integer(
        string='Po_count',
        required=False, compute='_compute_po_count')

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True, default=lambda self: self.env.company.currency_id.id)

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,
    )

    expected_currency_rate = fields.Float(
        compute="_compute_expected_currency_rate",
        digits=0,
    )

    purchase_manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')

    purchase_manual_currency_rate = fields.Float(
        string='Currency Rate',
        default=lambda self: self.expected_currency_rate,
        copy=False,
        digits=0,
        help="""
            Define the manual currency rate to apply to product pricing 
            and invoice generation when the above option is active.
            """
    )

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.update({'default_purchase_manual_currency_rate': self.expected_currency_rate})
        self = self.with_context(ctx)
        return super().copy(default=default)

    @api.constrains('purchase_manual_currency_rate')
    def _check_currency_rate(self):
        """Ensure the currency rate is strictly positive when record's currency differs from company currency."""
        for rec in self:
            if (
                    rec.currency_id
                    and rec.company_id
                    and rec.currency_id != rec.company_currency_id
                    and rec.purchase_manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        self.purchase_manual_currency_rate = self.expected_currency_rate

    def refresh_currency_rate(self):
        for po in self:
            po.purchase_manual_currency_rate = po.expected_currency_rate

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_expected_currency_rate(self):
        for so in self:
            if so.currency_id:
                so.expected_currency_rate = so.env['res.currency']._get_conversion_rate(
                    from_currency=so.company_currency_id,
                    to_currency=so.currency_id,
                    company=so.company_id,
                    date=fields.Date.context_today(self),
                )
            else:
                so.expected_currency_rate = 1

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    def write(self, vals):
        """
                Override write method to enforce constraint that all analytic distributions
                in lines are backed by budgeted accounts.

                Args:
                    vals (dict): Fields to update.

                Returns:
                    bool: Result of super().write()
                """
        res = super().write(vals)
        for line in self.requisition_line_ids:
            line.constrain_account_to_analytic()
        return res

    @api.depends('currency_id', 'requisition_line_ids', 'requisition_line_ids.qty',
                 'requisition_line_ids.price_unit', 'requisition_line_ids.amount_incurrency')
    def _compute_amount_incurrency(self):
        """
                Computes the total requisition amount in the selected currency.
                Aggregates the currency-converted amount from all requisition lines.
                """
        for rec in self:
            rec.amount_incurrency = sum(rec.requisition_line_ids.mapped('amount_incurrency'))

    @api.depends('requisition_line_ids', 'requisition_line_ids.account_id',
                 'requisition_line_ids.analytic_distribution', 'requisition_line_ids.qty',
                 'requisition_line_ids.price_unit', 'request_date')
    def _compute_budget_warning_message(self):
        """
                Computes the budget warnings by checking:
                - If any analytic account's budget will be exceeded.
                - If any account-only budget (without analytic) will be exceeded.
                Updates `budget_warning_message` and `over_budget_text` fields.
                """
        for requisition in self:
            over_budget_text = ''
            budget_warning_message = ""
            anlytic_dict = requisition.requisition_line_ids._get_analytic_accounts_amounts()

            if anlytic_dict:
                analytic_text_message, over_budgets = requisition.get_analytic_text_message(
                    anlytic_dict)
                budget_warning_message += analytic_text_message
                over_budget_text += over_budgets

            acounts_lines = requisition.requisition_line_ids._get_accounts_residual_amount()

            # if acounts_lines:
            #     account_message, account_over_budgets = requisition.get_account_message(
            #         acounts_lines)
            #     budget_warning_message += account_message
            #     if over_budget_text and account_over_budgets:
            #         over_budget_text += '/'
            #     over_budget_text += account_over_budgets
            requisition.budget_warning_message = budget_warning_message
            requisition.over_budget_text = over_budget_text

    def get_analytic_text_message(self, analytic_dict=None):
        """
                Check if any analytic account's budget is exceeded by this requisition.

                Args:
                    analytic_dict (dict): {analytic_id: amount}

                Returns:
                    tuple: (Warning message str, over_budget_text str)
                """
        if analytic_dict is None:
            analytic_dict = {}
        message = ''
        over_budgets = ''
        for analytic, amount in analytic_dict.items():

            account_ids_list = self._get_accounts_for_analytic(analytic)  # returns a list
            budget_contains_my_account = self.env['account.budget.post'].sudo().search([
                ('company_id', '=', self.company_id.id)
            ]).filtered(
                lambda b:
                any(account_id in b.account_ids.ids for account_id in account_ids_list))

            analytic_ids = [int(a) for a in analytic.split(',')]
            for analytic in analytic_ids:
                analytic_id = int(analytic)
                budget_lines = self.env['budget.line'].sudo().search(
                    [('date_from', '<=', self.request_date),
                     ('date_to', '>=', self.request_date),
                     ('budget_analytic_id.state', 'not in', ['canceled', 'draft']),
                     ('company_id', '=', self.company_id.id),
                     ('general_budget_id', 'in', budget_contains_my_account.ids)])

                keys_list = []

                for req_line in self.requisition_line_ids:
                    keys_list += [int(i) for k in
                                  req_line.analytic_distribution.keys() for i in
                                  k.split(',')]

                # print('budget_linessss', budget_lines)
                if budget_lines:
                    analytic = self.env['account.analytic.account'].sudo().browse(analytic_id)
                    for line in budget_lines:
                        fnames = line._get_plan_fnames()
                        analytic_accounts = [line[fname].id for fname in fnames
                                             if
                                             line[fname]]
                        if analytic_id in analytic_accounts:
                            if abs(line.achieved_amount) + amount > abs(line.budget_amount):
                                over_budgets += f"[{line.id},{abs(line.achieved_amount) + amount - abs(line.budget_amount)}]" + '/'
                                # message += f'* Analytic account {analytic.display_name} will exceed the budget planned amount in budget {line.budget_analytic_id.name} \n'

                                message += f"The Purchase Requisition amount exceeds the the planned amount for this cost center ( {analytic.display_name} ). Please change the cost center or submit a budget transfer request   \n"
        # by  amount {abs(line.practical_amount) + amount - abs(line.planned_amount)}
        return message, over_budgets

    def _get_accounts_for_analytic(self, analytic):
        """
                Get list of all unique account_ids used on lines that reference the given analytic.

                Args:
                    analytic (str or int): Analytic account ID as string or int.

                Returns:
                    list: List of account.account IDs.
                """
        account_ids = []
        for line in self.requisition_line_ids:
            if line.analytic_distribution and line.account_id:
                if analytic in line.analytic_distribution.keys():
                    account_ids.append(line.account_id.id)

        return account_ids

    def get_account_message(self, accounts=None):
        if accounts is None:
            accounts = {}
        message = ''
        over_budgets = ''
        for account, amount in accounts.items():
            budget_contains_my_account = self.env['account.budget.post'].sudo().search([
                ('company_id', '=', self.company_id.id)
            ]).filtered(
                lambda b: account in b.account_ids.ids)

            print('budget_contains_my_account', budget_contains_my_account)

            if budget_contains_my_account:
                budget_lines = self.env['budget.line'].sudo().search(
                    [('date_from', '<=', self.request_date), ('date_to', '>=', self.request_date),
                     ('budget_analytic_id.state', 'not in', ['canceled', 'draft']),
                     ('company_id', '=', self.company_id.id),
                     ('general_budget_id', 'in', budget_contains_my_account.ids)
                     ])

                keys_list = []

                for req_line in self.requisition_line_ids:
                    keys_list += [int(i) for k in req_line.analytic_distribution.keys() for i in k.split(',')]
                if budget_lines:
                    accoount_obj = self.env['account.account'].sudo().browse(account)
                    for line in budget_lines:
                        fnames = line._get_plan_fnames()
                        analytic_accounts = [line[fname].id for fname in fnames
                                             if
                                             line[fname]]

                        if (accoount_obj.id in line.general_budget_id.account_ids.ids) and (
                            any(x in keys_list for x in analytic_accounts)):

                            if abs(line.achieved_amount) + amount > abs(line.budget_amount):
                                over_budgets += f"[{line.id},{abs(line.achieved_amount) + amount - abs(line.budget_amount)}]" + '/'
                                # message += f'* Account {accoount_obj.display_name} will exceed the budget planned amount in budget {line.budget_analytic_id.name} by amount {abs(line.practical_amount) + amount - abs(line.planned_amount)} \n'
                                message += f"The Purchase Requisition amount exceeds the the planned amount for this account ( {accoount_obj.display_name} ). Please change the cost center or submit a budget transfer request\n"

        return message, over_budgets

    def unlink(self):
        for rec in self:
            if rec.approvement_state != 'draft':
                raise UserError(
                    _('You can not delete Purchase Requisition which is not in draft or cancelled or rejected state.'))
        #                raise UserError(_('You can not delete Purchase Requisition which is not in draft or cancelled or rejected state.'))
        return super().unlink()

    @api.depends('purchase_ids')
    def _compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.purchase_ids)

    @api.depends('requisition_line_ids',
                 'requisition_line_ids.qty',
                 'requisition_line_ids.product_id')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(
                [line.price_unit * line.qty for line in rec.requisition_line_ids])

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        if self.vendor_id:
            return {'domain': {'purchase_id': [('partner_id', '=', self.vendor_id.id)]}}
        return {'domain': {'purchase_id': []}}

    @api.onchange('type')
    def _onchange_type(self):
        if self.type != 'variation':
            self.purchase_id = False
            self.vendor_id = False

    @api.onchange('purchase_vendor_ids')
    def _onchange_purchase_vendor(self):
        if self.purchase_vendor_ids:
            for line in self.requisition_line_ids:
                line.partner_id = self.purchase_vendor_ids.ids
        else:
            for line in self.requisition_line_ids:
                line.partner_id = False

    @api.onchange('department_ids')
    def _onchange_department_ids(self):
        if self.department_ids:
            analytics = self.department_ids.mapped('analytic_account_id.id')
            if analytics:

                total_lines = len(analytics)
                percent = round(100.0 / total_lines, 2)
                percentages = [percent] * total_lines
                total_percentage = sum(percentages)
                difference = round(100.0 - total_percentage, 2)
                if difference != 0:
                    percentages[0] += difference

                analytic_dict = {}
                for index, an in enumerate(analytics):
                    analytic_dict[str(an)] = percentages[index]
                for line in self.requisition_line_ids:
                    line.analytic_distribution = analytic_dict
                    return
        else:
            for line in self.requisition_line_ids:
                line.analytic_distribution = {}

    @api.constrains('total_amount',
                    'purchase_id',
                    'type',
                    'requisition_line_ids')
    def _amount_limit_constraint(self):
        for record in self:
            if record.type and record.type == 'variation':
                if record.purchase_id and record.total_amount:
                    threshold = record.purchase_id.amount_untaxed * .25
                    if record.total_amount > threshold:
                        raise ValidationError(
                            _("The variation requisition exceeds 25% of the original commitment. Please change the requisition type."))

    def cancel(self):
        self.approvement_state = 'cancel'

    def submit_to_approve(self):
        if self.approvement_state == 'draft':
            self.approvement_state = 'pending'
            self.notify_department_head()

    def notify_department_head(self):
        department_head_users = self.get_department_head_users()
        if department_head_users:
            for user in department_head_users:
                self.action_send_requisition_approval_email(user, "New Requisition needs Approval")
                self.activity_schedule(
                    'kz_requisition_quintuple_approvals.mail_requisition_approval', user_id=user.id,
                    note=f'Requisition  {self.name} Needs Approval ')

            self.create_submit_approval_line(department_head_users)

    def create_submit_approval_line(self, users):
        users = [user.id for user in users]
        vals_dict = {
            'line_date': fields.Datetime.now(),
            'description': "Approval Request",
            'requester': self.env.user.id,
            'state': 'request',
            'send_to': users,
            'requisition_id': self.id
        }

        self.env['requisition.approval.line'].sudo().create(vals_dict)

    def create_approval_line(self):

        lines = self.approval_line_ids.filtered(lambda l: l.state == 'request')
        lines = sorted(lines, key=lambda l: l.create_date, reverse=True)
        if lines:
            line = lines[0]
            line.approved = True
        vals_dict = {
            'line_date': fields.Datetime.now(),
            'description': "Approval Done",
            'approver_id': self.env.user.id,
            'state': 'approval',
            'requisition_id': self.id
        }

        self.env['requisition.approval.line'].sudo().create(vals_dict)

    def create_reject_line(self):
        lines = self.approval_line_ids.filtered(lambda l: l.state == 'request')
        lines = sorted(lines, key=lambda l: l.create_date, reverse=True)
        if lines:
            line = lines[0]
            line.rejected = True
        vals_dict = {
            'line_date': fields.Datetime.now(),
            'description': "Requisition Rejected",
            'rejecter_id': self.env.user.id,
            'state': 'rejection',
            'requisition_id': self.id
        }
        self.env['requisition.approval.line'].sudo().create(vals_dict)

    def get_group_name(self, group):
        group_name = ''
        if group:
            group_name = 'kz_requisition_quintuple_approvals.' + group
        return group_name

    def get_groups_flow(self):
        groups_flow = ["department_head", "budget_controller", "re_head_of_unit", "cfo", "re_ceo"]
        return groups_flow

    def button_approve(self):
        groupes_flow = self.get_groups_flow()
        approval_group = self.env.context.get('approve_group')
        group_name = self.get_group_name(approval_group)
        if self.env.user.has_group(group_name):
            if approval_group == 'budget_controller' and not self.env.context.get(
                    'approve_anyway') and self.budget_warning_message:
                return self._get_approve_wizard()
            new_state = approval_group + '_approval'
            self.approvement_state = new_state
            self.close_activity(self.env.user)
            self.current_group = approval_group
            self.create_approval_line()
            if groupes_flow.index(approval_group) == (len(groupes_flow) - 1):
                self.approvement_state = 'approved'
                # self.notify_users()
                self.notify_creator(
                    f"A purchase order is ready to be created on purchase requisition {self.name}")
            elif groupes_flow.index(approval_group) < (len(groupes_flow) - 1):
                next_group_index = groupes_flow.index(approval_group) + 1
                next_group = groupes_flow[next_group_index]
                self.notify_group(next_group)

    def close_activity(self, user):
        mail_activity = self.env.ref('kz_requisition_quintuple_approvals.mail_requisition_approval')
        activity_name = mail_activity.name if mail_activity else "Anonymous"
        notifications = self.activity_ids.filtered(lambda n: n.display_name == activity_name)
        if notifications:
            for n in notifications:
                n._action_done()

    def update_after_resunbmission(self, vals_list):
        quantity_dict = vals_list[0]
        pricce_dict = vals_list[1]
        for line in self.requisition_line_ids:
            if line.product_id.id in quantity_dict.keys():
                line.qty = quantity_dict.get(line.product_id.id)
            if line.product_id.id in pricce_dict.keys():
                line.price_unit = pricce_dict.get(line.product_id.id)

    def _get_approve_wizard(self):
        wizard = self.env['reject.warning.wizard'].create({
            'requisition_id': self.id,
            'mode': 'approve'
        })
        return {
            'name': 'Approval Warning',
            'type': 'ir.actions.act_window',
            'res_model': 'reject.warning.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'kz_requisition_quintuple_approvals.view_reject_warning_wizard').id,
            'target': 'new',
            'res_id': wizard.id,
        }

    def reject_requisition(self):

        if self.env.context.get('reject_anyway'):
            self.approvement_state = 'rejected'
            self.message_post(subject="Requisition Rejected", message_type="notification",
                              body=f"Requisition has been rejected by {self.env.user.name}",
                              )
            self.notify_creator(f"Requisition {self.name} has been rejected")
            self.create_reject_line()
            self.close_activity(self.env.user)
        else:
            wizard = self.env['reject.warning.wizard'].create({
                'requisition_id': self.id,
                'mode': 'reject'
            })
            return {
                'name': 'Reject Warning',
                'type': 'ir.actions.act_window',
                'res_model': 'reject.warning.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'kz_requisition_quintuple_approvals.view_reject_warning_wizard').id,
                'target': 'new',
                'res_id': wizard.id,
            }

    def create_new_version(self):
        new_version = self.copy()
        new_version.original_requisition_id = self.id
        self.replacement_requisition_id = new_version.id

    def action_show_replacement(self):
        self.ensure_one()

        # Get the action for the purchase requisition
        requisition_action = self.env['ir.actions.act_window']._for_xml_id(
            'material_purchase_requisitions.action_material_purchase_requisition')

        # Set the res_id to open the form view directly for the specific record
        requisition_action.update({
            'res_id': self.replacement_requisition_id.id,  # Open the specific record
            'view_mode': 'form',  # Set to form view
            'view_type': 'form',
            'views': [
                (self.env.ref(
                    'material_purchase_requisitions.material_purchase_requisition_form_view').id,
                 'form')],
            'target': 'current',
        })
        return requisition_action

    def action_show_resubmitted(self):
        self.ensure_one()

        # Get the action for the purchase requisition
        requisition_action = self.env['ir.actions.act_window']._for_xml_id(
            'material_purchase_requisitions.action_material_purchase_requisition')

        # Set the res_id to open the form view directly for the specific record
        requisition_action.update({
            'res_id': self.resubmitted_requisition_id.id,  # Open the specific record
            'view_mode': 'form',  # Set to form view
            'view_type': 'form',
            'views': [
                (
                    self.env.ref(
                        'material_purchase_requisitions.material_purchase_requisition_form_view').id,
                    'form')],
            'target': 'current',
        })

        return requisition_action

    def action_show_resubmitted_original(self):
        self.ensure_one()

        # Get the action for the purchase requisition
        requisition_action = self.env['ir.actions.act_window']._for_xml_id(
            'material_purchase_requisitions.action_material_purchase_requisition')

        # Set the res_id to open the form view directly for the specific record
        requisition_action.update({
            'res_id': self.resubmitted_original_requisition_id.id,  # Open the specific record
            'view_mode': 'form',  # Set to form view
            'view_type': 'form',
            'views': [
                (
                    self.env.ref(
                        'material_purchase_requisitions.material_purchase_requisition_form_view').id,
                    'form')],
            'target': 'current',
        })

        return requisition_action

    def action_show_original(self):
        self.ensure_one()

        # Get the action for the purchase requisition
        requisition_action = self.env['ir.actions.act_window']._for_xml_id(
            'material_purchase_requisitions.action_material_purchase_requisition')

        # Set the res_id to open the form view directly for the specific record
        requisition_action.update({
            'res_id': self.original_requisition_id.id,  # Open the specific record
            'view_mode': 'form',  # Set to form view
            'view_type': 'form',
            'views': [
                (self.env.ref(
                    'material_purchase_requisitions.material_purchase_requisition_form_view').id,
                 'form')],
            'target': 'current',
        })

        return requisition_action

    def check_is_department_manager(self, emp_id):
        departments = self.env['hr.department'].sudo().search([('manager_id', '=', emp_id)])
        return len(departments) > 0

    def get_nearest_manager(self, employee):
        if not employee.parent_id:
            return False
        if self.check_is_department_manager(employee.parent_id.id):
            return employee.parent_id

        return self.get_nearest_manager(employee.parent_id)

    def get_department_head_users(self):
        users = []
        if self.employee_id:
            nearest_manager = self.get_nearest_manager(self.employee_id)
            if nearest_manager:
                users.append(nearest_manager.user_id)
                return users
        approve_group = self.env.ref(
            'kz_requisition_quintuple_approvals.department_head_backup')
        users = approve_group.users
        if users:
            return users
        return users

    def notify_group(self, group):
        if group:
            group_name = self.get_group_name(group)

            approve_group = self.env.ref(group_name)
            users = approve_group.users
            if users:
                for user in users:
                    self.action_send_requisition_approval_email(user,
                                                                "New Requisition needs pproval")
                    self.activity_schedule(
                        'kz_requisition_quintuple_approvals.mail_requisition_approval',
                        user_id=user.id,
                        note=f'Requisition  {self.name} Needs Approval ')
                self.create_submit_approval_line(users)

    def return_to_draft(self):
        self.approvement_state = 'draft'
        self.current_group = ''
        self.state = 'draft'

    def notify_users(self):

        purchase_group = self.env.ref('purchase.group_purchase_user')
        users = purchase_group.users
        users_ids = users + self.create_uid

        if users_ids:
            message = f'A purchase order is ready to be created on purchase requisition {self.name}'
            for user in users_ids:
                self.action_send_requisition_approval_email(user, message)
                self.activity_schedule('kz_requisition_quintuple_approvals.mail_po_ready',
                                       user_id=user,
                                       note=f'A purchase order is ready to be created on purchase requisition {self.name}')

    def notify_creator(self, message):
        users_ids = [self.create_uid]
        partners = [self.create_uid.partner_id.id]

        if users_ids:
            for user in users_ids:
                self.action_send_requisition_approval_email(user, message)

                self.activity_schedule('kz_requisition_quintuple_approvals.po_created',
                                       user_id=user.id,
                                       note=message)

    def send_mail_to_vendor(self):
        if not self.purchase_vendor_ids:
            raise ValidationError(_("Purchase Vendor Is Mandatory"))
        self.ensure_one()
        lang = self.env.context.get('lang')

        ctx = {
            'default_model': 'material.purchase.requisition',
            'default_subject': self.name,
            'default_res_ids': self.ids,
            'default_partner_ids': self.purchase_vendor_ids.ids,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
        }
        if self.attacchment_ids:
            ctx['default_attachment_ids'] = self.attacchment_ids.ids

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def _fetch_additional_create_context(self):
        """To be supered to add for new purchase creates"""
        self.ensure_one()
        return {}

    def request_stock(self):
        if not self.purchase_vendor_ids:
            raise ValidationError(_("Purchase Vendor is Mandatory"))
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']

        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']

        purchases = []
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))
            if any(line.requisition_type == 'internal' for line in rec.requisition_line_ids):
                if not rec.location_id.id:
                    raise UserError(_('Select Source location under the picking details.'))
                if not rec.custom_picking_type_id.id:
                    raise UserError(_('Select Picking Type under the picking details.'))
                if not rec.dest_location_id:
                    raise UserError(_('Select Destination location under the picking details.'))
                picking_vals = {
                    'partner_id': rec.employee_id.sudo().address_home_id.id,
                    'location_id': rec.location_id.id,
                    'location_dest_id': rec.dest_location_id and rec.dest_location_id.id or rec.employee_id.dest_location_id.id or rec.employee_id.department_id.dest_location_id.id,
                    'picking_type_id': rec.custom_picking_type_id.id,  # internal_obj.id,
                    'note': rec.reason,
                    'custom_requisition_id': rec.id,
                    'origin': rec.name,
                    'company_id': rec.company_id.id,
                }
                stock_id = stock_obj.sudo().create(picking_vals)
                delivery_vals = {
                    'delivery_picking_id': stock_id.id,
                }
                rec.write(delivery_vals)

            po_dict = {}
            for line in rec.requisition_line_ids:
                if line.requisition_type == 'internal':
                    pick_vals = rec._prepare_pick_vals(line, stock_id)
                    move_obj.sudo().create(pick_vals)
                if line.requisition_type == 'purchase':  # 10/12/2019
                    if not line.partner_id:
                        raise UserError(
                            _('Please enter at least one vendor on Requisition '
                              'Lines for Requisition Action Purchase'))
                    for partner in line.partner_id:
                        if partner not in po_dict:
                            po_vals = {
                                'partner_id': partner.id,
                                'currency_id': rec.currency_id.id,
                                'purchase_manual_currency_rate': rec.purchase_manual_currency_rate,
                                'date_order': fields.Date.today(),
                                'company_id': rec.company_id.id,
                                'scope_of_work_attacchment_ids': rec.attacchment_ids.ids,
                                'shareholders_attacchment_ids': rec.shareholders_attacchment_ids.ids,
                                'board_attacchment_ids': rec.board_attacchment_ids.ids,
                                'custom_requisition_id': rec.id,
                                'origin': rec.name,
                                **self._fetch_additional_create_context()
                            }
                            purchase_order = purchase_obj.create(po_vals)
                            purchases.append(purchase_order.id)
                            po_dict.update({partner: purchase_order})
                            po_line_vals = rec.with_context(
                                partner_id=partner)._prepare_po_line(
                                line, purchase_order)
                            purchase_line_obj.sudo().create(po_line_vals)
                        else:
                            purchase_order = po_dict.get(partner)
                            po_line_vals = rec.with_context(partner_id=partner)._prepare_po_line(
                                line, purchase_order)

                            purchase_line_obj.sudo().create(po_line_vals)
                rec.state = 'stock'
            message = f'A purchase order created on purchase requisition {self.name}'
            rec.notify_creator(message)
            rec.approvement_state = 'completed'
            rec.purchase_ids = purchases

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):

        po_line_vals = {
            'product_id': line.product_id.id,
            'name': f"{line.product_id.name}\n{line.description}",
            'product_qty': line.qty,
            'product_uom': line.uom.id,
            'date_planned': fields.Date.today(),
            # 'price_unit': line.product_id.standard_price,
            'price_unit': line.price_unit or 0.0,
            'order_id': purchase_order.id,

            # 'account_analytic_id': self.analytic_account_id.id,
            'analytic_distribution': line.analytic_distribution or False,
            'account_id': line.account_id.id or False,
            'custom_requisition_line_id': line.id
        }
        return po_line_vals

    def action_show_budgets(self):
        view = self.env.ref('kz_requisition_quintuple_approvals.budget_line_view_tree_wizard')
        return {

            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'name': 'Budget Lines',  # Optional: gives the name to the action
            'res_model': 'budget.line',
            'views': [(view.id, 'list')],
            'view_id': view.id,
            'domain': [],
            'target': 'new',
            'context': {'requisition': self.id}
        }

    def action_show_po(self):
        # for rec in self:
        #     purchase_action = self.env.ref('purchase.purchase_rfq')
        #     purchase_action = purchase_action.sudo().read()[0]
        self.ensure_one()
        purchase_action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_rfq')
        purchase_action['domain'] = str([('id', '=', self.purchase_ids.ids)])
        return purchase_action

    def action_send_requisition_approval_email(self, user, message):
        for requisition in self:
            if user.email:
                # Get the base URL for generating the requisition link
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                requisition_url = f"{base_url}/web#id={requisition.id}&model=material.purchase.requisition&view_type=form"

                # Email subject and body with user's name and a button for the requisition link
                subject = f"Requisition: {requisition.name}"
                body_html = f"""
                    <p>Dear Mr {user.name},</p>
                    <p>{message}</p>
                    <p>Please click the button below to view the requisition:</p>
                    <p>
                        <a href="{requisition_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; border-radius: 5px;">
                            View Requisition
                        </a>
                    </p>
                    <p>Best regards \n {requisition.env.user.name}</p>
                """

                # Prepare email values
                mail_values = {
                    'subject': subject,
                    'email_from': requisition.company_id.srn_notification_email,
                    'body_html': body_html,
                    'email_to': user.email,  # Email of the passed user object
                    'author_id': self.env.user.partner_id.id,  # Current user as sender
                }

                # Send the email
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.sudo().send()

                # Add a message in the chatter
                requisition.message_post(body=f"Email sent to {user.name} with requisition link.")
