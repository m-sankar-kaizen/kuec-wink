# -*- coding: utf-8 -*-
from odoo import models, fields, _, api


class KickOffMeeting(models.TransientModel):
    _name = 'kick.off.meeting'
    _description = 'Kick Off Meeting'

    kick_off_meeting_date = fields.Datetime(string='Kick Off Meeting Date')
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender Rfq')

    def action_choose_date(self):
        self.ensure_one()
        self.tender_rfq_id.kick_off_meeting_date = self.kick_off_meeting_date
        return {'type': 'ir.actions.act_window_close'}


