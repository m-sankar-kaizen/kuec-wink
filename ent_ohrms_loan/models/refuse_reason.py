# -*- coding: utf-8 -*-
"""
Model for capturing and processing reasons when an HR loan or housing advance is refused.

Key Features:
-------------
- Stores the refusal reason and the user who refused the loan.
- Supports dynamic linking to a loan record via context.
- Updates the related loan's state field when confirmed.
- Triggers a predefined email template for refusal notification if provided.

Typical Usage:
--------------
This model is used via a popup wizard triggered by the "Refuse" button on a loan request.
"""

from odoo import models, fields


class RefuseReason(models.Model):
    """Model to log refusal reasons for HR loan requests."""
    _name = 'refuse.reason'
    _description = 'Refuse Reason'

    reason = fields.Char(
        string="Refuse Reason",
        help="Brief reason for refusing the loan or housing advance request."
    )

    refused_by_user_id = fields.Many2one(
        'res.users',
        string="Refused By",
        default=lambda rec: rec.env.user.id,
        help="The user who refused the request. Defaults to the current user."
    )

    loan_id = fields.Many2one(
        'hr.loan',
        string="Related Loan",
        help="Loan / Housing Advance record this refusal is associated with."
    )

    def action_on_confirm(self):
        """
        Confirm the refusal reason and apply necessary changes:
        - Sets the state of the related loan to the value passed via context.
        - Sends an email using the template passed in context.

        Context Keys Expected:
        -----------------------
        - field_name: (str) name of the Many2one field on this model linking to the loan (e.g. 'loan_id')
        - state_field: (str) field on the loan to update state (e.g. 'state')
        - state_value: (str) new state value to set on the loan (e.g. 'refuse')
        - refusal_template_id: (str) XML ID of the email template to use for refusal notification

        Example:
        --------
        Called via a wizard with context:
        {
            'default_loan_id': loan.id,
            'field_name': 'loan_id',
            'state_field': 'state',
            'state_value': 'refuse',
            'refusal_template_id': 'ent_ohrms_loan.email_template_refusal_notification_hr_loan',
        }
        """
        context = self.env.context
        field_name = context.get('field_name')
        state_field = context.get('state_field')
        state_value = context.get('state_value')
        template_xml_id = context.get('refusal_template_id')

        # Resolve the related loan using the context-specified field
        related_record = self[field_name] if field_name else None

        if related_record:
            # Set the state of the related record if applicable
            if state_field and state_value:
                related_record[state_field] = state_value

            # Send email notification if template is provided
            if template_xml_id:
                template = self.env.ref(template_xml_id, raise_if_not_found=False)
                if template:
                    template.with_context(user=self.env.user).send_mail(
                        related_record.id, force_send=True
                    )
