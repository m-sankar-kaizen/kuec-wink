from odoo import models, fields


# [Start] Class for displaying all approval requests ########################################

class AllApprovals(models.Model):
    _name = 'all.approvals'
    _inherit = 'hiring.request'
    _description = 'All Hiring Approvals'
# [End] Class for displaying all approval requests ########################################
