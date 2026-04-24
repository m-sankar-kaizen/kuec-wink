# -*- coding: utf-8 -*-
from odoo import models, fields, _, api, Command
from odoo.exceptions import ValidationError


class ResearchDevelopment(models.Model):
    _name = 'research.development'
    _description = 'Research And Development'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name', required=True, default="New")
    title = fields.Char(string='Title', required=True)
    employee_id = fields.Many2one('hr.employee', string='Requester', required=True,
                                  default=lambda self: self.env.user.employee_id)
    employee_parent_id = fields.Many2one(related='employee_id.parent_id', string='Department Head')
    department_id = fields.Many2one(related='employee_id.department_id', string='Department')
    partner_ids = fields.Many2many('res.partner', string='Innovation Partners',
                                   domain="[('is_vendor', '=', True)]")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approval', 'Approvals'),
            ('confirm', 'Confirmed'),
            ('reject', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string='State',
        default='draft',
        required=True,
        tracking=True,
    )
    approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('dep_head', 'Department Head'),
            ('cio', 'Chief Investment Officer'),
            ('cco', 'Chief Commercialization Officer'),
            ('approved', 'Approved'),
            ('reject', 'Rejected'),
        ],
        string='Approval State',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    description = fields.Html(string='Description')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    material_purchase_requisition_ids = fields.One2many('material.purchase.requisition',
                                                        'research_development_id',
                                                        'Purchase Requisition')

    @api.constrains('partner_ids')
    def _constrains_partner_ids(self):
        for record in self:
            draft_vendors = record.partner_ids.filtered(lambda p: p.state == 'draft')
            if draft_vendors:
                raise ValidationError("You cannot choose the partner who is in 'Draft' state")

            expired_vendors = record.partner_ids.filtered(lambda p: p.has_expired_documents)
            if expired_vendors:
                raise ValidationError(
                    "You cannot choose a partner who has expired documents, Please update the expired documents.")

    def action_create_pr(self):
        self.ensure_one()
        if self.approval_state == 'approved':
            if not self.material_purchase_requisition_ids:
                self.material_purchase_requisition_ids = [Command.create({
                    'purchase_vendor_ids': [Command.link(partner.id)],
                    'employee_id': self.employee_id.id,
                    'company_id': self.company_id.id,
                    'research_development_id': self.id,
                }) for partner in self.partner_ids]
        else:
            raise ValidationError(_("The R&D request has not been approved yet."))

    def action_purchase_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Requisitions'),
            'res_model': 'material.purchase.requisition',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.material_purchase_requisition_ids.ids)],
            'views': [(False, 'list'), (False, 'form')],
        }

    def action_submit_for_approval(self):
        """Move the R&D request to approval state and initialize approval cycle."""
        self.ensure_one()
        self.state = 'approval'
        self.approval_state = 'dep_head'
        user = self.employee_parent_id.user_id
        if not user:
            raise ValidationError(_("The Department Head for this employee has no linked user."))

        # Schedule activity for department head
        activity_type = self.env.ref(
            'kaz_research_and_development.mail_activity_type_r_and_d',
            raise_if_not_found=False
        )
        if activity_type:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary="R&D Request Approval Required",
                note="Please review and approve the R&D request.",
                user_id=user.id,
            )

    def action_department_head_approval(self):
        self.ensure_one()
        if self.env.user.employee_id.id != self.employee_parent_id.id:
            raise ValidationError(_(
                "You are not the Department Head for this employee."
            ))
        self.approval_state = 'cio'
        self._mark_activity_done()
        self.notify_group_users(
            summary='R&D Request Awaiting CIO Approval',
            note=(
                f"The R&D request '{self.name}' submitted by "
                f"{self.employee_id.name} has been approved by the Department Head "
                "and is now awaiting your review and approval."
            ),
            group_xml_id='kaz_contact_approval.group_contact_qualifier'
        )

    def action_cio_approval(self):
        self.ensure_one()
        self.approval_state = 'cco'
        self.notify_group_users(
            summary='R&D Request Awaiting CCO Approval',
            note=(
                f"The R&D request '{self.name}' submitted by "
                f"{self.employee_id.name} has been approved by the CIO "
                "and is now awaiting your review and approval."
            ),
            group_xml_id='kaz_contact_approval.group_contact_qualifier'
        )

    def action_reject_dep_head(self):
        self.ensure_one()
        if self.env.user.employee_id.id != self.employee_parent_id.id:
            raise ValidationError(_(
                "You are not the Department Head for this employee."
            ))
        self._mark_activity_done()
        self.action_reject()

    def action_rfc_dep_head(self):
        self.ensure_one()
        if self.env.user.employee_id.id != self.employee_parent_id.id:
            raise ValidationError(_(
                "You are not the Department Head for this employee."
            ))
        self._mark_activity_done()
        self.action_reset_to_draft()

    def action_approve(self):
        """Approve the R&D request, create Purchase Request, and move state to approved."""
        self.ensure_one()
        self.state = 'confirm'
        self.approval_state = 'approved'
        self._mark_activity_done()

    def action_reject(self):
        """Reject the R&D request and move to rejected state."""
        self.ensure_one()
        self.state = 'reject'
        self.approval_state = 'reject'
        self._mark_activity_done()

    def action_cancel(self):
        """Cancel the R&D request."""
        self.ensure_one()
        self.state = 'cancel'
        self.approval_state = 'draft'
        self._mark_activity_done()

    def action_rfc(self):
        self.ensure_one()
        self.action_reset_to_draft()

    def action_reset_to_draft(self):
        """Reset the R&D request to draft."""
        self.ensure_one()
        self.state = 'draft'
        self.approval_state = 'draft'
        self._mark_activity_done()

    @property
    def _get_group_hierarchy(self):
        return [
            'kaz_research_and_development.group_research_dep_head_kuec',
            'kaz_research_and_development.group_research_cio_kuec',
            'kaz_research_and_development.group_research_cco_kuec',
        ]

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
        activity_type_xml_id = activity_type_xml_id or 'kaz_research_and_development.mail_activity_type_r_and_d'
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
        activity_type_xml_id = activity_type_xml_id or 'kaz_research_and_development.mail_activity_type_r_and_d'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('research.development') or 'New'
        return super().create(vals_list)
