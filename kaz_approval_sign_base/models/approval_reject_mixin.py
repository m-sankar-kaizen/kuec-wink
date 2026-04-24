# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ApprovalRejectMixin(models.AbstractModel):
    """
    Mixin class to add a sequential approval workflow to any model.
    It provides fields for the approval state, signature, and the user who signed.
    """
    _name = 'approval.reject.mixin'
    _description = 'Approval Reject Mixin'
    # Class attribute to be defined by the inheriting model
    _parent_record = None

    # --- Approval Fields ---

    sequence = fields.Integer(
        string='Sequence',
        readonly=True,
        help='The sequence number of this approval step within the parent document.'
    )

    request_type = fields.Selection(
        selection=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('rfc', 'Return for Correction'),
        ],
        default='rfc',
        string='Request Type',
        required=True,
    )

    parent_state_at_request = fields.Char(string='Parent State At Request', copy=False)

    signature = fields.Binary(
        string='Signature',
        compute='_compute_signature',
        inverse='_inverse_signature',
        store=True,
        readonly=False,
        help='Digital signature of the approving user.'

    )

    def _get_default_signature(self):
        return self.env.user.display_name

    current_display_name = fields.Char(string="Signature Name", default=_get_default_signature)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    # company_code = fields.Selection(related="company_id.company_code", string="Company Code")

    next_action = fields.Char(string='Next Action')

    reason = fields.Text(
        string='Reason',
        compute='_compute_reason',
        inverse='_inverse_reason',
        store=True,
        readonly=False,
    )

    @api.depends('request_type', 'current_display_name')
    def _compute_reason(self):
        for record in self:
            if record.request_type == 'approve':
                record.reason = f"Approved by {record.current_display_name}"
            else:
                record.reason = record.reason or ""

    def _inverse_reason(self):
        # Allow users to edit reason directly; just write the value back
        for record in self:
            record.reason = record.reason

    @api.depends('current_display_name')
    def _compute_signature(self):
        for record in self:
            # Only set signature automatically if empty
            if not record.signature:
                record.signature = self.env.user.sign_signature or ""

    def _inverse_signature(self):
        # Allow user override. Nothing special needed.
        for record in self:
            record.signature = record.signature

    def _get_next_action_args(self):
        """
        Helper function to determine the arguments, keyword arguments, and context
        to be used when calling the 'next_action' method on the parent record.

        Inheriting models can override this to pass custom data.

        :return: (args, kwargs, context) tuple
        """
        # Always include signed=True in the context
        context = self.env.context.copy()
        context['signed'] = True

        return [], {}, context

    def action_confirm_request(self):
        """
        Action to set the record as approved, capture the signature
        (if available), and record the signing user and date.
        Super this action to achieve your result
        """
        self.ensure_one()

        if not self._parent_record or self._parent_record not in self._fields:
            raise ValidationError(
                _("Configuration Error: The inheriting model must define the class attribute _parent_record with the name of the Many2one link to the parent."))

        if self.request_type in ['approve', 'reject'] and not self.signature:
            raise ValidationError(_("Signature is Required"))

        if self.next_action:
            # Use the explicitly defined _parent_record attribute
            args, kwargs, next_action_context = self._get_next_action_args()
            parent_field = self._parent_record
            parent_record = self[parent_field]
            action_method = self.next_action

            parent_record_ctx = parent_record.with_context(next_action_context)
            if hasattr(parent_record, action_method):
                # Call the method on the parent record with the 'signed' context
                try:
                    return getattr(parent_record_ctx, action_method)(*args, **kwargs)
                except Exception as e:
                    _logger.info("Error calling next_action '%s' on parent model '%s': %s",
                                 action_method, parent_record._name, str(e))
                    raise
            else:
                raise ValidationError(
                    _("The next action method '%s' does not exist on the parent model '%s'.") %
                    (action_method, parent_record._name))
