# -*- coding: utf-8 -*-
from odoo import api, models, _


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    def action_refuse_reason_apply(self):
        summary = _("Recruitment Form Rejected")
        note = _(
            f"The recruitment request has been rejected by {self.env.user.display_name}. "
            "Please review the submitted recruitment form"
        )
        for rec in self:
            for applicant in rec.applicant_ids:
                applicant._perform_action('rejected', applicant.user_id, summary, note)
        return super().action_refuse_reason_apply()
