# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class KuecDocumentSubmission(models.Model):
    _name = 'kuec.document.submission'
    _description = 'WINK Document Submission'
    _order = 'submitted_date desc'
    _inherit = ['mail.thread']

    order_id = fields.Many2one(
        'sale.order',
        string='Service Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    requirement_id = fields.Many2one(
        'kuec.service.document',
        string='Document Requirement',
        required=True,
        ondelete='restrict',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Submitted By',
        required=True,
        ondelete='restrict',
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Uploaded File',
        ondelete='set null',
    )
    filename = fields.Char(
        string='File Name',
    )
    state = fields.Selection([
        ('draft', 'Not Uploaded'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('change_required', 'Change Required'),
        ('rejected', 'Rejected'),
    ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    coordinator_notes = fields.Text(
        string='Coordinator Notes',
        help="Reason for rejection or change request. Visible to customer.",
    )
    submitted_date = fields.Datetime(
        string='Submitted',
        readonly=True,
    )
    reviewed_date = fields.Datetime(
        string='Reviewed',
        readonly=True,
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        readonly=True,
        ondelete='set null',
    )
    requirement_name = fields.Char(
        related='requirement_id.name',
        string='Document Name',
        store=True,
    )
    is_required = fields.Selection(
        related='requirement_id.requirement',
        string='Requirement Level',
        store=True,
    )

    def action_approve(self):
        """Coordinator approves the submitted document."""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'reviewed_date': fields.Datetime.now(),
            'reviewed_by': self.env.uid,
            'coordinator_notes': False,
        })
        self._notify_customer('approved')

    def action_request_change(self):
        """Coordinator requests changes to the submitted document."""
        self.ensure_one()
        if not self.coordinator_notes:
            raise UserError(
                "Please add coordinator notes explaining what needs to change."
            )
        self.write({
            'state': 'change_required',
            'reviewed_date': fields.Datetime.now(),
            'reviewed_by': self.env.uid,
        })
        self._notify_customer('change_required')

    def action_reject(self):
        """Coordinator rejects the submitted document."""
        self.ensure_one()
        if not self.coordinator_notes:
            raise UserError(
                "Please add a rejection reason in the coordinator notes."
            )
        self.write({
            'state': 'rejected',
            'reviewed_date': fields.Datetime.now(),
            'reviewed_by': self.env.uid,
        })
        self._notify_customer('rejected')

    def _notify_customer(self, decision):
        """Post a chatter message and send email notification."""
        state_labels = {
            'approved': 'Approved',
            'change_required': 'Change Required',
            'rejected': 'Rejected',
        }
        label = state_labels.get(decision, decision)
        body = (
            f"Document <strong>{self.requirement_name}</strong> "
            f"marked as: <strong>{label}</strong>"
        )
        if self.coordinator_notes:
            body += f"<br/>Notes: {self.coordinator_notes}"

        self.order_id.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        template = self.env.ref(
            'kuec_service_catalogue.kuec_doc_review_notification',
            raise_if_not_found=False,
        )
        if template:
            template.sudo().send_mail(self.id, force_send=True)
