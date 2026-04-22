from odoo import models, fields
from odoo.exceptions import ValidationError

class ValidateAccountMove(models.TransientModel):
    _inherit = 'validate.account.move'

    def validate_move(self):
        unapproved_moves = self.move_ids.filtered(
            lambda
                r: r.company_id.company_code == 'KUEC' and r.kuec_approval_state != 'approved'
        )
        if unapproved_moves:
            list_items = "\n".join([f"• {name}" for name in
                                    unapproved_moves.mapped('display_name')])
            raise ValidationError(
                f"The following entries in KUEC are not approved:\n\n{list_items}"
            )

        return super().validate_move()
