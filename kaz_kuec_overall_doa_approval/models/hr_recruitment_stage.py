# -*- coding: utf-8 -*-
from odoo import models, _, api, fields
from odoo.exceptions import ValidationError


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    is_approval_stage = fields.Boolean(string='Approval Stage')

    @api.constrains('hired_stage', 'is_approval_stage')
    def _check_stage_constraints(self):
        for record in self:
            # 1. Check that only one stage is hired_stage
            if record.hired_stage:
                existing_hired = self.sudo().search([
                    ('id', '!=', record.id),
                    ('hired_stage', '=', True)
                ])
                if existing_hired:
                    raise ValidationError(_(
                        "Only one stage can be set as the 'Hired Stage'. "
                        "Please unset it from other stages first."
                    ))

            # 2. Check that only one stage is is_approval_stage
            if record.is_approval_stage:
                existing_approval = self.sudo().search([
                    ('id', '!=', record.id),
                    ('is_approval_stage', '=', True)
                ])
                if existing_approval:
                    raise ValidationError(_(
                        "Only one stage can be set as the 'Approval Stage'. "
                        "Please unset it from other stages first."
                    ))

            # 3. Check that a stage cannot be both hired_stage and is_approval_stage
            if record.hired_stage and record.is_approval_stage:
                raise ValidationError(_(
                    "A stage cannot be both 'Hired Stage' and 'Approval Stage'."
                ))
