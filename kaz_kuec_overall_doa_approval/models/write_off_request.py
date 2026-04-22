# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError


class WriteOffRequest(models.Model):
    _name = 'write.off.request'
    _description = 'Write Off Request'
    _check_company_auto = True
    _inherit = ['approval.base.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, default=_('New'))
    account_move_id = fields.Many2one('account.move', string='Account Move', copy=False)
    journal_id = fields.Many2one('account.journal', string='Journal')
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method')
    partner_bank_id = fields.Many2one('res.partner.bank', string='Partner Bank')
    payment_type = fields.Selection(
        selection=[
            ('inbound', 'Receive Money'),
            ('outbound', 'Send Money'),
        ],
        string='Payment Type',
        default='inbound'
    )
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    payment_date = fields.Date(string='Payment Date')
    communication = fields.Char(string='Memo')
    payment_difference = fields.Monetary(string='Payment Difference', currency_field='currency_id')
    writeoff_account_id = fields.Many2one('account.account', string='Write Off Account')
    writeoff_label = fields.Char(string='Write Off Label')
    line_ids = fields.Many2many('account.move.line', string='Lines', copy=False)
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
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
    is_readonly = fields.Boolean(string='Is Readonly', copy=False)
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment', copy=False)
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )
    write_off_approval_ids = fields.One2many('write.off.request.approval',
                                             'write_off_id',
                                             string='Approval/Rejection/Return History')
    account_payment_ids = fields.One2many('account.payment', 'write_off_id',
                                          string="Account Payments")
    manual_currency_rate = fields.Float(
        'Rate', copy=False, digits=0
    )

    def action_open_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Write Off'),
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.account_payment_ids.ids)],
        }

    @api.depends('kuec_approval_state', 'kuec_board_attachment')
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment
            )

    @property
    def _approval_model(self):
        return 'write.off.request.approval'

    @property
    def _approval_line(self):
        return self.write_off_approval_ids

    @property
    def _approval_state(self):
        return 'kuec_approval_state'

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_write_off_id': self.id
        }

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Write-Off Request Requires Your Review")
        note = _(
            f"The Write-Off Request has been approved by {self.env.user.display_name} "
            "Please review the submitted Write-Off Request form and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def submit_to_approve(self):
        self.ensure_one()
        summary = _("Write-Off Request Requires Your Review")
        note = _(
            f"The Write-Off Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Write-Off Request form and proceed with the next steps."
        )
        users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
        self._perform_action('finance_procurement_approval', users, summary, note)

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ccoe_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_ccoe')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.payment_difference > 100_000:
                self._perform_common_action('ceo_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ceo')
            else:
                self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.amount > 1_000_000:
                self._perform_common_action('board_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_board')
            else:
                self._perform_action('approved')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_board_approval(self):
        self.ensure_one()
        if self.kuec_approval_state == 'board_approval' and not self.kuec_board_attachment:
            raise ValidationError(
                _("Please upload the required Board Approval attachment before proceeding.")
            )
        if self._context.get('signed', False):
            self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_board_approval')


    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Write-Off Request Rejected")
            note = _(
                f"The Write-Off Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Write-Off Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Reject Write-Off', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Write-Off Request Returned for Correction")
            note = _(
                f"The Write-Off Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Write-Off Request form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('write.off.request') or _('New')
        return super().create(vals_list)

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal items.
        :return: An action opening the account.payment.register wizard.
        '''
        if self.kuec_approval_state != 'approved':
            raise UserError(_(
                "You can register a payment only when the Write-Off Request is Approved."
            ))

        if self.account_payment_ids:
            raise ValidationError(_(
                "A payment has already been registered for this Write-Off Request.\n\n"
                "Multiple payments are not allowed."
            ))
        context = {
            'active_model': 'account.move.line',
            'active_ids': self.line_ids.ids,
            'default_journal_id': self.journal_id.id,
            'default_write_off_id': self.id,
            'default_payment_method_line_id': self.payment_method_line_id.id,
            'default_partner_bank_id': self.partner_bank_id.id,
            'default_currency_id': self.currency_id.id,
            'default_writeoff_account_id': self.writeoff_account_id.id,
            'default_writeoff_label': self.writeoff_label,
            'default_payment_type': self.payment_type,
            'default_custom_user_amount': self.amount,
            'default_amount': self.amount,
            'default_payment_date': self.payment_date,
            'default_communication': self.communication,
            'default_manual_currency_rate': self.manual_currency_rate,
            'force_manual_currency_rate': True,
            'default_is_readonly': True,
            'default_is_approved': True,
            'default_payment_difference_handling': 'reconcile',
            'default_early_payment_discount_mode': True,
        }

        return self.line_ids.action_register_payment(ctx=context)
