from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    po_incomplete_months_limit = fields.Integer(
        string="PO Incomplete Age Limit (Months)",
        default=12,
        config_parameter="kaz_po_close_out.po_incomplete_months_limit",
        help="Number of months after which draft/incomplete "
             "POs appear in the report.",
    )