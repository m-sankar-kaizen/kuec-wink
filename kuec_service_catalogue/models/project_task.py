# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class ProjectTaskWink(models.Model):
    _inherit = 'project.task'

    def write(self, vals):
        if 'stage_id' in vals:
            new_stage = self.env['project.task.type'].browse(vals['stage_id'])
            if not new_stage.exists():
                return super().write(vals)

            for task in self:
                # If we are changing stages, check compliance on WINK portal requests
                if task.sale_order_id and task.sale_order_id.wink_is_portal_request:
                    old_stage = task.stage_id
                    if not old_stage:
                        continue
                    # If moving to a new stage (from the very first stage 'sequence 1-10' typically 'New')
                    if (old_stage.id != new_stage.id
                            and old_stage.sequence <= 10
                            and new_stage.sequence > old_stage.sequence):
                        all_approved, pending = task.sale_order_id._wink_all_required_docs_approved()
                        if not all_approved:
                            # requirement_name can be False; ensure join receives strings
                            pending_names = [str(p or _('Unknown')) for p in pending]
                            raise UserError(_(
                                "Compliance Hard-Gate: You cannot move this task out of the 'New' stage because the customer has missing or unapproved documents: %s"
                            ) % ", ".join(pending_names))
        return super().write(vals)
