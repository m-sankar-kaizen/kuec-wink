from odoo import models, fields
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_external_recruiter = fields.Boolean()

    def _get_checklist_domain(self):
        self.ensure_one()
        domain = super()._get_checklist_domain()
        if self.is_external_recruiter:
            new_condition = ('for_external_recruiter', '=', True)
            if not domain:
                return [new_condition]
            if isinstance(domain[0], tuple):
                return ['|', new_condition] + domain
            return ['|'] + [new_condition] + domain
        return domain

    def _get_checklist_create_vals(self, idx, checklist):
        res = super()._get_checklist_create_vals(idx=idx,
                                                 checklist=checklist)
        res['for_external_recruiter'] = checklist.for_external_recruiter
        return res

    def _get_attachment_domain(self):
        domain = super()._get_attachment_domain()
        if self.is_external_recruiter:
            domain += [('is_external_recruiter', '=', True)]
        return domain

    def _check_partner_type(self):
        if not (self.is_vendor or self.is_customer or self.is_external_recruiter):
            raise ValidationError(
                "The partner must be either a Vendor or "
                "a Customer or a External Recruiter."
            )
