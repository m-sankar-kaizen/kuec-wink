# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError


class TenderBafoRequest(models.Model):
    _name = 'tender.bafo.request'
    _description = 'Tender Bafo Request'
    _check_company_auto = True

    sequence = fields.Integer(string='Sequence', required=True)
    reason = fields.Char(string='Reason', required=True)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ', required=True)
    bafo_type = fields.Selection(
        selection=[
            ('all', 'All Bidders'),
            ('top_2', 'Top 2 Commercial Vendors'),
            # ('technical', 'Best Technical Vendors'),
            ('best_x', 'The Technical and Commercial offers'),
        ],
        string='BAFO Type',
        required=True,
    )
    best_x_bids = fields.Integer(string="Best 'X' Bids")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    requested_user_id = fields.Many2one('res.users', string='Requested User',
                                        default=lambda self: self.env.user)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='State',
        default='draft',
        required=True,
    )
    created_tender_rfq_id = fields.Many2one('tender.rfq', string='Created Tender')

    @api.constrains('bafo_type', 'best_x_bids')
    def _check_best_x_bids(self):
        for rec in self:
            if rec.bafo_type == 'best_x' and (not rec.best_x_bids or rec.best_x_bids <= 0):
                raise ValidationError(
                    _("You must set 'Best X Bids' to a value greater than 0 when BAFO Type is 'The best Overall offer (top X)'.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            # Initialize cache entry if not present
            if company_id not in sequence_cache:
                # Fetch latest sequence for this company
                last_record = self.sudo().search(
                    [('company_id', '=', company_id),
                     ('tender_rfq_id', '=', vals.get('tender_rfq_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        recs = super().create(vals_list)
        recs.notify_tender_user()

        return recs

    def notify_tender_user(self):
        activity_type = self.env.ref('kaz_vendor_management.mail_activity_type_tender_bafo')

        for rec in self:
            group = self.env.ref('purchase.group_purchase_manager')
            if group:
                # Schedule activity for each user in the group
                for user in group.users:
                    rec.tender_rfq_id.activity_schedule(
                        activity_type_id=activity_type.id,
                        user_id=user.id,
                        summary="BAFO Request",
                        note=_(
                            "A BAFO request has been created.\n"
                            "Type: %s\n"
                            "Reason: %s"
                        ) % (rec.bafo_type, rec.reason)
                    )

    def action_approve(self):
        self.ensure_one()
        self.state = 'approved'
        if self.tender_rfq_id.state == 'under_review':
            self.tender_rfq_id.state = 'bafo'
        self.tender_rfq_id.message_post(
            body=_(
                f"BAFO request {self.sequence}). {self.reason} has been APPROVED.\n"
                f"Type: {self.bafo_type}\n"
            )
        )

        self.tender_rfq_id.tender_bid_ids.write({'state': 'bafo_selected'})

        datas = self.tender_rfq_id._get_child_trender_data()
        top_bids, rejected_bids = self.tender_rfq_id._get_top_and_rejected_bid(
            bafo_type=self.bafo_type)
        if self.bafo_type == 'best_x' and self.best_x_bids > 0:
            top_bids = top_bids[:self.best_x_bids]
        partner_ids = top_bids.mapped('partner_id')
        default_partners = self.tender_rfq_id.partner_ids.ids
        all_partner_ids = default_partners + partner_ids.ids
        for data in datas:
            data.update({
                # 'state': 'active',
                'is_bafo': True,
                'bafo_type': self.bafo_type,
                'is_exclusive': True,
                'partner_ids': [Command.set(all_partner_ids)],
            })
        tender_rfq_id = self.env['tender.rfq'].create(datas)
        self.created_tender_rfq_id = tender_rfq_id.id
        tender_rfq_id.action_activate()
        tender_rfq_id.action_send_bafo_mail()

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'

        self.tender_rfq_id.message_post(
            body=_(
                f"BAFO request {self.sequence}). {self.reason} has been Rejected.\n"
                f"Type: {self.bafo_type}\n"
            )
        )
