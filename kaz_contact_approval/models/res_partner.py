# -*- coding: utf-8 -*-
from odoo import fields, models, _, Command, api
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_attachment_line_ids = fields.One2many('partner.attachment.line', 'partner_id')
    partner_checklist_ids = fields.One2many('partner.checklist', 'partner_id')
    state = fields.Selection(
        [('draft', 'Draft'), ('pre_approved', 'Pre-Approved'),
         ('qualified', 'Qualified'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft',
        tracking=True,
        string='Status',
    )
    is_vendor = fields.Boolean("Is Vendor")
    is_customer = fields.Boolean("Is Customer")
    # is_employee = fields.Boolean("Is Employee")
    partner_category_ids = fields.Many2many('partner.category')
    has_expired_documents = fields.Boolean("Has Expired Documents",
                                           compute='_compute_has_expired_documents')
    show_partner_category_required = fields.Boolean(
        compute='_compute_show_partner_category_required',
    )
    is_readonly = fields.Boolean("Is Readonly", compute='_compute_readonly_form')

    @api.depends('state')
    def _compute_readonly_form(self):
        for record in self:
            record.is_readonly = record.state in ['approved', 'rejected']

    def _compute_show_partner_category_required(self):
        """This will compute the partner category required for the partner since the
        employee_ids can only be ready by privileged users this can override that"""
        for record in self:
            partner = record.sudo()

            record.show_partner_category_required = (
                    not partner.employee_ids and
                    not partner.parent_id
            )

    def unlink(self):
        for partner in self:
            if partner.state != 'draft':
                raise UserError(_("You cannot delete a partner while it's not in draft state."))
        return super().unlink()

    @api.depends('partner_attachment_line_ids.is_expired')
    def _compute_has_expired_documents(self):
        for record in self:
            record.has_expired_documents = False

            if record.partner_attachment_line_ids:
                record.has_expired_documents = any(
                    line.is_expired for line in record.partner_attachment_line_ids
                )

    def _get_checklist_domain(self):
        self.ensure_one()
        domain = []
        if self.is_customer and self.is_vendor:
            domain = ['|', ('for_customer', '=', True), ('for_vendor', '=', True)]
        elif self.is_customer:
            domain = [('for_customer', '=', True)]
        elif self.is_vendor:
            domain = [('for_vendor', '=', True)]
        return domain

    def action_add_checklist_lines(self):
        self.ensure_one()
        domain = self._get_checklist_domain()
        if not domain:
            self.partner_checklist_ids = [Command.clear()]
            return
        checklist_ids = self.env['partner.checklist.conf'].search(domain)
        self.partner_checklist_ids = [Command.clear()] + [
            Command.create(self._get_checklist_create_vals(idx, checklist)) for idx, checklist in
            enumerate(checklist_ids)
        ]

    def _get_checklist_create_vals(self, idx, checklist):
        return {
            'sequence': idx + 1,
            'name': checklist.name,
            'for_customer': checklist.for_customer,
            'for_vendor': checklist.for_vendor,
        }

    def _get_attachment_domain(self):
        self.ensure_one()
        domain = [('company_type', '=', self.company_type)]
        if self.is_customer:
            domain += [('is_customer', '=', True)]
        if self.is_vendor:
            domain += [('is_vendor', '=', True)]
        return domain

    def action_add_partner_attachment_lines(self):
        self.ensure_one()
        domain = self._get_attachment_domain()
        attachment_lines = self.env['attachment.attachment'].search(domain).mapped(
            'checklist_line_ids')
        if attachment_lines:
            self.partner_attachment_line_ids = [Command.clear()] + [
                Command.create({
                    'sequence': idx + 1,
                    'name': attachment.name,
                    'attachment_is_required': attachment.attachment_is_required,
                    'expiry_date_required': attachment.expiry_date_required,
                    'attachment_type': attachment.attachment_type,
                }) for idx, attachment in enumerate(attachment_lines)
            ]
        else:
            self.partner_attachment_line_ids = [Command.clear()]

    def _check_field_values(self, fields_list):
        for record in self:
            missing_fields = []
            for field_name in fields_list:
                if not getattr(record, field_name, False):
                    missing_fields.append(field_name)
            if missing_fields:
                raise ValidationError(
                    f"The following fields are required and cannot be empty: {', '.join(missing_fields)}"
                )

    def notify_group_users(self, summary, note, group_xml_id, group_hierarchy=False,
                           activity_type_xml_id=False):
        """Send activity to users in a group.
        If group_hierarchy is provided, only send to users who are *exclusively* in this group,
        excluding any users that also belong to higher-level groups.
        """
        self.ensure_one()
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return

        users = group.users

        if not group_hierarchy:
            group_hierarchy = self._get_group_hierarchy

        # Filter out users in higher-level groups if hierarchy is provided
        if group_hierarchy and group_xml_id in group_hierarchy:
            current_index = group_hierarchy.index(group_xml_id)
            higher_groups = group_hierarchy[current_index + 1:]
            higher_users = self.env['res.users']
            for high_group_xml_id in higher_groups:
                high_group = self.env.ref(high_group_xml_id, raise_if_not_found=False)
                if high_group:
                    higher_users |= self.env['res.users'].search(
                        [('groups_id', 'in', high_group.id)])
            users = users - higher_users

        # Default activity type if not provided
        activity_type_xml_id = activity_type_xml_id or 'kaz_contact_approval.mail_activity_type_contact_approval'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)

        for user in users:
            self.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=summary,
                note=note,
                user_id=user.id,
            )

    def _mark_activity_done(self, activity_type_xml_id=False):
        """Mark pending activities of a specific type as done."""
        self.ensure_one()
        activity_type_xml_id = activity_type_xml_id or 'kaz_contact_approval.mail_activity_type_contact_approval'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    @property
    def _get_group_hierarchy(self):
        return [
            'kaz_contact_approval.group_contact_pre_approver',
            'kaz_contact_approval.group_contact_qualifier',
            'kaz_contact_approval.group_contact_admin',
        ]

    @property
    def _get_pre_approval_fields(self):
        return ['email']

    def _check_partner_type(self):
        if not (self.is_vendor or self.is_customer):
            raise ValidationError(
                "The partner must be either a Vendor or a Customer."
            )

    def action_pre_approve(self):
        self.ensure_one()
        if self.sudo().employee_ids:
            self.state = 'approved'
            self.message_post(body="Auto-approved: Partner is an employee.")
            return

        fields_list = self._get_pre_approval_fields
        if not (self.phone or self.mobile):
            fields_list.append('phone')
        self._check_partner_type()
        self._check_field_values(fields_list)
        if not self.partner_checklist_ids:
            self.action_add_checklist_lines()
        self._validate_attachment_lines()
        self.state = 'pre_approved'
        self.notify_group_users(
            summary='Partner Pre-Approval',
            note='This partner has been pre-approved and requires your review.',
            group_xml_id='kaz_contact_approval.group_contact_qualifier'
        )

    def action_qualified(self):
        if self.partner_checklist_ids and self.partner_checklist_ids.filtered(
                lambda rec: not rec.is_checked):
            raise ValidationError(
                _('There are incomplete checklists. Please complete them first.'))
        if not self.partner_attachment_line_ids:
            self.action_add_partner_attachment_lines()
        self._validate_attachment_lines()
        self.state = 'qualified'
        self._mark_activity_done()
        self.notify_group_users(
            summary='Partner Qualified',
            note='This partner has been qualified and requires your attention.',
            group_xml_id='kaz_contact_approval.group_contact_admin'
        )

    def _validate_attachment_lines(self):
        invalid_lines = self.partner_attachment_line_ids.filtered(
            lambda rec: (rec.attachment_is_required and not (
                    rec.attachment_link or rec.ir_attachment_ids)) or
                        (rec.expiry_date_required and not rec.expiry_date)
        )
        if invalid_lines:
            raise ValidationError(
                _('Some Attachment lines are incomplete. Please make sure all required attachments and expiry dates are filled.')
            )
        expired_lines = self.partner_attachment_line_ids.filtered(lambda rec: rec.is_expired)
        if expired_lines:
            raise ValidationError(
                _('Some Attachment lines are expired. Please make sure all attachments Up to date.')
            )

    def action_approve(self):
        self._validate_attachment_lines()
        self.state = 'approved'
        self._mark_activity_done()

    def action_draft(self):
        self.state = 'draft'

    def action_reject(self):
        self.ensure_one()
        return {
            'name': _('Reject Reason'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'contact.reject.reason',
            'context': {
                'default_partner_id': self.id
            }
        }
