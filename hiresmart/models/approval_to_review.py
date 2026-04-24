from odoo import models, fields


# [Start] Class for displaying approval requests that are to be reviewed ########################################

class ApprovalToReview(models.Model):
    _name = 'approval.to.review'
    _inherit = 'hiring.request'
    _description = 'Approvals to Review'
# [End] Class for displaying approval requests that are to be reviewed ########################################
