# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.osv import expression



class HrApplicant(models.Model):
    """
    Extension of the hr.applicant model to add custom logic for stage transition.

    This model allows an applicant to move to the next recruitment stage,
    enforcing group-based approval permissions defined on each stage.

    It ensures:
        - Only authorized users from the configured approval group can advance applicants.
        - Transitions are based on the sequence order of available stages.
    """
    _inherit = 'hr.applicant'

    company_code = fields.Selection(related='company_id.company_code')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        job_id = self._context.get('default_job_id')

        # Original domain
        search_domain = [('job_ids', '=', False)]

        if job_id:
            search_domain = ['|', ('job_ids', '=', job_id)] + search_domain

        if stages:
            search_domain = ['|', ('id', 'in', stages.ids)] + search_domain

        # ✅ ADD company domain safely
        company_domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ]

        # Combine both domains properly
        final_domain = expression.AND([
            search_domain,
            company_domain
        ])

        stage_ids = stages.sudo()._search(final_domain, order=stages._order)
        x = stages.browse(stage_ids)
        return x

    def change_state(self):
        """
        Move the applicant to the next stage in the recruitment pipeline,
        if the current user has the required approval rights.

        Raises:
            ValidationError: If the current user does not belong to the
                             approval group for the current stage.
        """
        current_stage = self.stage_id

        # Get all applicable stages for the job or global stages (job_ids=False)
        stage_ids = self.env['hr.recruitment.stage'].search([
            '&',
            '|',
            ('job_ids', '=', False),
            ('job_ids', 'in', [self.job_id.id]),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ], order='sequence asc').ids

        # Enforce stage-level approval group restriction
        if current_stage.approval_groups_id:
            if self.env.user.id not in current_stage.approval_groups_id.users.ids:
                raise ValidationError(
                    "You are not authorized to approve this stage. "
                    "Please contact an authorized approver."
                )

        # Debug print to log current stage and last stage (optional)

        # If current stage is not the last one, move to the next stage
        if current_stage.id != stage_ids[-1]:
            try:
                current_index = stage_ids.index(current_stage.id)
                self.stage_id = stage_ids[current_index + 1]
            except (ValueError, IndexError):
                raise ValidationError("Cannot determine the next stage.")
