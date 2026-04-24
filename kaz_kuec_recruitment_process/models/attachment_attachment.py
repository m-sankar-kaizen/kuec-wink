from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Attachment(models.Model):
    _inherit = 'attachment.attachment'

    is_external_recruiter = fields.Boolean(
        string="Is External Recruiter")

    @api.constrains('is_vendor',
                    'is_customer',
                    'is_external_recruiter')
    def _check_customer_or_vendor(self):
        for record in self:
            if not record.is_vendor and not record.is_customer and not record.is_external_recruiter:
                raise ValidationError(
                    "At least one of 'Is Customer' or 'Is Vendor' or 'Is External Recruiter' must be enabled."
                )


