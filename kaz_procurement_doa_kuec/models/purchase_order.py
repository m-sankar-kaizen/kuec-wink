# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['approval.base.mixin', 'purchase.order']

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    budget_warning_message = fields.Text(
        string="Budget Warning", compute='_compute_budget_warning_message', store=True, copy=False)
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('board_approval', 'KUEC Board Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    purchase_approval_ids = fields.One2many(
        'purchase.order.approval', 'purchase_id',
        string="Approval/Rejection/Return History")

    is_readonly = fields.Boolean(string='Is Readonly', copy=False)
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment', copy=False)
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )

    def _check_company_access(self):
        return self.company_code in ['KUEC']

    @property
    def _approval_model(self):
        return 'purchase.order.approval'

    @property
    def _approval_line(self):
        return self.purchase_approval_ids

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_purchase_id': self.id
        }

    def _get_department_head(self):
        self.ensure_one()
        employee = self.user_id.employee_id
        if not employee:
            raise ValidationError(
                _("No Employee found. Please create an employee for this user")
            )
        manager = employee.parent_id
        if not manager:
            raise ValidationError(
                _("No department head found. Please assign a manager to the employee’s department.")
            )
        if not manager.user_id:
            raise ValidationError(
                _("The department head does not have a linked user. Please configure a user for the manager.")
            )
        return manager

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Purchase Order Request Requires Your Review")
        note = _(
            f"The Purchase Order Request has been approved by {self.env.user.display_name} "
            "Please review the submitted Purchase Order Request form and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def action_lock_po(self):
        self.ensure_one()
        self.is_readonly = True

    def action_unlock_po(self):
        self.ensure_one()
        self.is_readonly = False

    def submit_to_approve(self):
        if self._check_company_access():
            self.action_lock_po()
            self.kuec_approval_state = 'department_approval'
            summary = _("Purchase Order Request Requires Your Review")
            note = _(
                f"The Purchase Order Request has been Requested by {self.env.user.display_name} "
                "Please review the submitted Purchase Order Request form and proceed with the next steps."
            )
            manager = self._get_department_head()
            self._perform_action('department_approval', manager.user_id, summary, note)

    def action_hod_reject(self):
        self.ensure_one()
        self._validate_hod()
        return self.action_reject_request()

    def action_hod_rfc(self):
        self.ensure_one()
        self._validate_hod()
        return self.action_rfc_request()

    def action_hod_approval(self):
        self.ensure_one()
        self._validate_hod()
        if self._context.get('signed', False):
            self._perform_common_action('finance_procurement_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.requisition_id and self.amount_total <= 1_000_000 or self.amount_total <= 500_000:
                self._perform_action('approved')
            else:
                self._perform_common_action('ccoe_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ccoe')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.requisition_id or self.amount_total <= 3_000_000:
                self._perform_action('approved')
            else:
                self._perform_common_action('ceo_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ceo')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.amount_total <= 10_000_000:
                self._perform_action('approved')
            else:
                self._perform_common_action('board_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_board')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_board_approval(self):
        self.ensure_one()
        if self.kuec_approval_state == 'board_approval' and not self.kuec_board_attachment:
            raise ValidationError(
                _("Please upload the required Board Approval attachment before proceeding. If the record is locked, unlock it first and upload the attachment.")
            )
        if self._context.get('signed', False):
            self._perform_action('approved')
            self.action_lock_po()
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_board_approval')

    @api.depends('kuec_approval_state', 'kuec_board_attachment')
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment
            )

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Purchase Order Request Rejected")
            note = _(
                f"The Purchase Order Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Purchase Order Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.state = 'cancel'
            return True
        else:
            return self._open_approve_reject_wizard('Reject Purchase Order', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Purchase Order Request Returned for Correction")
            note = _(
                f"The Purchase Order Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Purchase Order Request form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            self.state = 'draft'
            self.action_unlock_po()
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def button_cancel(self):
        for order in self:
            order.kuec_approval_state = 'cancel'

        return super().button_cancel()

    def button_draft(self):
        for order in self:
            order.kuec_approval_state = 'draft'
            order.action_unlock_po()

        return super().button_draft()

    def _get_analytic_accounts_amounts(self):
        """
        Computes the total budgeted amount per analytic account for this line.

        Returns:
            dict: {analytic_account_id: amount}
        """
        analytic_dict = {}
        for line in self.order_line:
            amount = line.product_qty * line.price_unit
            if line.analytic_distribution:
                for analytic_id, percent in line.analytic_distribution.items():
                    analytic_dict[analytic_id] = analytic_dict.get(analytic_id,
                                                                   0) + (
                                                         percent / 100) * amount
        return analytic_dict

    def _get_accounts_residual_amount(self):
        """
        Computes the residual (non-distributed) budget amount per account.

        Returns:
            dict: {account_id: amount}
        """
        accounts_dict = {}
        for line in self.order_line:
            if line.account_id:
                amount = line.product_qty * line.price_unit
                residual_amount = amount if amount > 0 else 0
                accounts_dict[line.account_id.id] = accounts_dict.get(
                    line.account_id.id, 0) + residual_amount
        return accounts_dict

    def _get_accounts_for_analytic(self, analytic):
        """
                Get list of all unique account_ids used on lines that reference the given analytic.

                Args:
                    analytic (str or int): Analytic account ID as string or int.

                Returns:
                    list: List of account.account IDs.
                """
        account_ids = []
        for line in self.order_line:
            if line.analytic_distribution and line.account_id:
                if analytic in line.analytic_distribution.keys():
                    account_ids.append(line.account_id.id)

        return account_ids

    def get_analytic_text_message(self, analytic_dict=None):
        if analytic_dict is None:
            analytic_dict = {}
        message = ''
        over_budgets = ''
        for analytic, amount in analytic_dict.items():

            # Handle comma-separated analytic IDs (e.g., '3,74')
            analytic_ids = [int(a.strip()) for a in str(analytic).split(',') if
                            a.strip()]
            for analytic_id in analytic_ids:
                account_ids_list = self._get_accounts_for_analytic(analytic_id)
                budget_contains_my_account = self.env[
                    'account.budget.post'].sudo().search([]).filtered(
                    lambda b:
                    any(account_id in b.account_ids.ids for account_id in
                        account_ids_list))

                budget_lines = self.env['budget.line'].sudo().search(
                    [('date_from', '<=', self.date_order),
                     ('date_to', '>=', self.date_order),
                     ('account_id', '=', analytic_id),
                     ('budget_analytic_id.state', 'not in', ['confirmed']),
                     ('general_budget_id', 'in',
                      budget_contains_my_account.ids)])

                if budget_lines:
                    analytic_account = self.env[
                        'account.analytic.account'].sudo().browse(analytic_id)
                    for line in budget_lines:
                        if abs(line.achieved_amount) + amount > abs(
                                line.budget_amount):
                            over_budgets += f"[{line.id},{abs(line.achieved_amount) + amount - abs(line.budget_amount)}]" + '/'
                            message += f"The Purchase Requisition amount exceeds the planned amount for this cost center ( {analytic_account.display_name} ). Please change the cost center or submit a budget transfer request  \n"

        return message, over_budgets

    def get_account_message(self, accounts=None):
        if accounts is None:
            accounts = {}
        message = ''
        over_budgets = ''
        for account, amount in accounts.items():

            budget_contains_my_account = self.env['account.budget.post'].sudo().search([]).filtered(
                lambda b: account in b.account_ids.ids)

            if budget_contains_my_account:
                budget_lines = self.env['budget.line'].sudo().search(
                    [('date_from', '<=', self.date_order), ('date_to', '>=', self.date_order),
                     ('account_id', '=', False),
                     ('budget_analytic_id.state', 'not in', ['canceled', 'draft']),
                     ('general_budget_id', 'in', budget_contains_my_account.ids)])
                if budget_lines:
                    account_obj = self.env['account.account'].sudo().browse(account)
                    for line in budget_lines:
                        if abs(line.achieved_amount) + amount > abs(line.budget_amount):
                            over_budgets += f"[{line.id},{abs(line.achieved_amount) + amount - abs(line.budget_amount)}]" + '/'
                            message += f"The Purchase Requisition amount exceeds the the planned amount for this account ( {account_obj.display_name} ). Please change the cost center or submit a budget transfer request\n"

        return message, over_budgets

    @api.depends('order_line', 'order_line.account_id',
                 'order_line.analytic_distribution', 'order_line.product_qty',
                 'order_line.price_unit', 'date_order')
    def _compute_budget_warning_message(self):
        """
                Computes the budget warnings by checking:
                - If any analytic account's budget will be exceeded.
                - If any account-only budget (without analytic) will be exceeded.
                Updates `budget_warning_message` fields.
                """
        for order in self:
            over_budget_text = ''
            budget_warning_message = ""
            analytic_dict = order._get_analytic_accounts_amounts()
            if analytic_dict:
                analytic_text_message, over_budgets = order.get_analytic_text_message(
                    analytic_dict)
                budget_warning_message += analytic_text_message
                over_budget_text += over_budgets

            accounts_lines = order._get_accounts_residual_amount()

            if accounts_lines:
                account_message, account_over_budgets = order.get_account_message(
                    accounts_lines)
                budget_warning_message += account_message
                if over_budget_text and account_over_budgets:
                    over_budget_text += '/'
                over_budget_text += account_over_budgets
            order.budget_warning_message = budget_warning_message

    @api.constrains('amount_total')
    def _check_amount_without_pr(self):
        for order in self:
            if order.company_id.company_code in ['KUEC']:
                if order.custom_requisition_id or order.tender_rfq_id or order.contract_agreement_id or order.requisition_id:
                    continue

                limit = order.company_id.amount_po_without_pr

                # No restriction when limit = 0
                if not limit or limit <= 0:
                    continue

                # Check amount against limit
                if order.amount_total > limit:
                    raise UserError(_(
                        "The total amount (%.2f) exceeds the maximum allowed amount "
                        "of %.2f for Purchase Orders without a Purchase Requisition.\n\n"
                        "Please create a Purchase Requisition before creating this PO."
                    ) % (order.amount_total, limit))
