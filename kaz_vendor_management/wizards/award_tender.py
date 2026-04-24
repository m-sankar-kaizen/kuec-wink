# -*- coding: utf-8 -*-
from odoo import models, fields, _, api


class AwardTender(models.TransientModel):
    _name = 'award.tender'
    _description = 'Award Tender'

    tender_rfq_id = fields.Many2one('tender.rfq', 'Tender RFQ')
    tender_bid_ids = fields.One2many(related='tender_rfq_id.tender_bid_ids', string='Tender Bids')
    tender_bid_id = fields.Many2one('tender.bid', string='Tender Bid')
    reason = fields.Char('Reason')

    def action_award_tender(self):
        self.ensure_one()

        # self.tender_bid_id._action_award_bid()
        # ^^^^^ Has been moved to Tender RFQ, Refer: action_create_purchase

        other_bids = self.tender_bid_ids - self.tender_bid_id
        other_bids.write({'state': 'rejected'})

        self.tender_rfq_id.state = 'awarded'
        self.tender_bid_id.state = 'awarded'
        self.tender_rfq_id.awarded_tender_bid_id = self.tender_bid_id.id

        # Post message on current tender
        self.tender_rfq_id.message_post(
            body=_("Tender has been awarded to %s by %s.\n reason: %s") % (
                self.tender_bid_id.name,
                self.env.user.display_name,
                self.reason,
            )
        )

        # Handle parent tender if exists
        parent_tender = self.tender_rfq_id.tender_rfq_id
        if parent_tender:
            parent_tender.state = 'bafo_awarded'
            parent_tender.tender_bid_ids.write({'state': 'rejected'})

            # Post message on parent tender
            parent_tender.message_post(
                body=_("This tender has been marked as BAFO Awarded by %s.") % (
                    self.env.user.display_name
                )
            )

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _("Tender Awarded Successfully! 🎉"),
                'type': 'rainbow_man',
            }
        }
