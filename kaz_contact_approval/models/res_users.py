# -*- coding: utf-8 -*-
from odoo import models, api


class Users(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super(Users, self).create(vals_list)
        group_user = self.env.ref('base.group_user')

        for user in users:
            if not user.share and group_user in user.groups_id:
                user.partner_id.state = 'approved'

        return users