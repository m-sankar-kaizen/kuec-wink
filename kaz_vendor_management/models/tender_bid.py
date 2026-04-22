# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError


class TenderBid(models.Model):
    _name = 'tender.bid'
    _description = 'Tender Bidding'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'total_score desc'

    name = fields.Char(string='Name', required=True, default="New")
    title = fields.Char(related='tender_rfq_id.title')
    tender_state = fields.Selection(related='tender_rfq_id.state')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender')
    partner_ids = fields.Many2many('res.partner', string='Partners',
                                   compute='_compute_domain_partner_ids')

    partner_id = fields.Many2one(
        'res.partner',
        string='Bidder',
        compute='_compute_partner_id',
        inverse='_inverse_partner_id',
        store=True,
        domain="[('id', 'in', partner_ids)]",
    )

    bid_user_id = fields.Many2one(
        'res.users',
        string='Bidder User',
        compute='_compute_bid_user_id',
        inverse='_inverse_bid_user_id',
        store=True,
        index=True,
    )
    technical_evaluation_checklist_id = fields.Many2one(
        related='tender_rfq_id.technical_evaluation_checklist_id',
        string='Technical Evaluation Checklist')
    commercial_evaluation_checklist_id = fields.Many2one(
        related='tender_rfq_id.commercial_evaluation_checklist_id',
        string='Commercial Evaluation Checklist')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pre_qualify', 'Pre-Qualify'),
            ('evaluation', 'Evaluation'),
            ('bid_evaluated', 'Evaluated'),
            ('bafo_selected', 'BAFO Selected'),
            ('awarded', 'Awarded'),
            ('rejected', 'Rejected'),
        ],
        default='draft',
        string='State',
        tracking=True,
    )
    technical_user_ids = fields.Many2many(related='tender_rfq_id.technical_user_ids')
    commercial_user_ids = fields.Many2many(related='tender_rfq_id.commercial_user_ids')
    technical_score_weight = fields.Float(related='tender_rfq_id.technical_score_weight',
                                          string='Technical Weight (%)')
    commercial_score_weight = fields.Float(related='tender_rfq_id.commercial_score_weight',
                                           string='Commercial Weight (%)')
    technical_evaluation_checklist_ids = fields.One2many(
        'evaluation.checklist',
        'tender_bid_technical_id',
        string='Technical Evaluation Checklist'
    )
    commercial_evaluation_checklist_ids = fields.One2many(
        'evaluation.checklist',
        'tender_bid_commercial_id',
        string='Commercial Evaluation Checklist'
    )
    total_technical_score = fields.Float(
        string='Total Technical Score',
        compute='_compute_scores',
        store=True
    )
    total_commercial_score = fields.Float(
        string='Total Commercial Score',
        compute='_compute_scores',
        store=True
    )
    total_score = fields.Float(
        string='Total Overall Score',
        compute='_compute_scores',
        store=True
    )
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    manual_currency_rate = fields.Float('Rate', copy=False, digits=0,
                                        default=lambda self: self.expected_currency_rate)
    company_currency_id = fields.Many2one(string='Company Currency',
                                          related='company_id.currency_id', readonly=True)
    expected_currency_rate = fields.Float(compute="_compute_expected_currency_rate", digits=0)
    tender_bid_rfq_line_ids = fields.One2many('tender.bid.rfq.line', 'tender_bid_id',
                                              string='Bid RFQ Lines')
    is_portal = fields.Boolean('Is Portal', default=False)
    tender_checklist_ids = fields.One2many('tender.checklist', 'tender_bid_id',
                                           string='Tender Bid Checklists')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    total_amount = fields.Float(compute='_compute_total_amount', string='Total Amount')
    tender_bid_required_attachment_ids = fields.One2many('tender.bid.required.attachment',
                                                         'tender_bid_id',
                                                         string='Tender Bid Required Attachments')
    is_vendor = fields.Boolean(related='partner_id.is_vendor', string='Is Vendor')
    vendor_score = fields.Float(related='partner_id.vendor_score', string='Vendor Score')
    evaluation_rating = fields.Selection(related='partner_id.evaluation_rating',
                                         string='Evaluation Rating')
    tender_bid_approval_ids = fields.One2many('tender.bid.approval', 'tender_bid_id',
                                              string="Tender Bid Approval")
    rank = fields.Integer(
        string="Rank",
        compute="_compute_rank",
    )

    @api.onchange('tender_rfq_id')
    def _onchange_rfq_id(self):
        self.partner_id = False

    @api.depends('tender_rfq_id')
    def _compute_domain_partner_ids(self):
        for rec in self:
            if rec.tender_rfq_id and rec.tender_rfq_id.is_exclusive and rec.tender_rfq_id.partner_ids:
                rec.partner_ids = self.tender_rfq_id.partner_ids.ids
            else:
                partners = rec.env['res.partner'].search(
                    [('company_id', '=', rec.company_id.id), ('is_vendor', '=', True)])
                rec.partner_ids = partners.ids

    def _compute_display_name(self):
        if not self.env.context.get('tender_award_display'):
            return super()._compute_display_name()
        else:
            for rec in self:
                rec.display_name = f"{rec.partner_id.name} (#{rec.rank})"
            return True

    @api.depends('tender_rfq_id', 'total_score')
    def _compute_rank(self):
        for rec in self:
            if not rec.tender_rfq_id:
                rec.rank = 0
                continue

            # Get all bids for this tender
            all_bids = rec.tender_rfq_id.tender_bid_ids.filtered(
                lambda b: b.total_score is not None)

            if not all_bids:
                rec.rank = 0
                continue

            # Sort descending by total_score
            sorted_bids = sorted(all_bids, key=lambda b: b.total_score or 0, reverse=True)

            # Find this record's rank
            for idx, bid in enumerate(sorted_bids, start=1):
                if bid.id == rec.id:
                    rec.rank = idx
                    break
            else:
                # Record not in tender_bid_ids yet (new record)
                rec.rank = 0

    @api.constrains('partner_id')
    def _check_partner_has_user(self):
        for rec in self:
            if rec.partner_id and not rec.partner_id.user_ids:
                raise ValidationError(
                    "The selected partner has no user linked.\n"
                    "Please create a user for this partner before selecting."
                )

    def unlink(self):
        for bid in self:
            if bid.state != 'draft':
                raise UserError(_("You cannot delete a Bid while it's not in draft state."))
        return super().unlink()

    @api.depends('tender_bid_rfq_line_ids', 'tender_bid_rfq_line_ids.qty',
                 'tender_bid_rfq_line_ids.price_unit', 'manual_currency_rate')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.tender_bid_rfq_line_ids.mapped('amount_in_currency'))

    def _generate_awarded_letter(self):
        ...

    # def _action_award_bid(self):
    #     self.ensure_one()
    #     self.state = 'awarded'
    #     self._action_create_purchase_order()
    #     self._action_send_awarded_mail()

    def _action_create_purchase_order(self):
        self.ensure_one()

        if self.state != 'awarded':
            raise UserError(_("You can only create a Purchase Order from an awarded bid."))

        if not self.partner_id:
            raise UserError(_("The awarded bid has no vendor linked."))

        if not self.tender_bid_rfq_line_ids:
            raise UserError(_("There are no RFQ lines to create a Purchase Order."))

        # Create Purchase Order
        delivery_date = datetime.combine(self.tender_rfq_id.delivery_date, time.min)
        contract = self.company_id.contract_material if self.tender_rfq_id.order_type == 'material' else self.company_id.contract_service

        po_vals = {
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'tender_bid_id': self.id,
            'tender_rfq_id': self.tender_rfq_id.id,
            'date_planned': delivery_date,
            'order_type': self.tender_rfq_id.order_type,
            'order_line': [],
            'notes': contract
        }

        order_lines = []
        for line in self.tender_bid_rfq_line_ids:
            if not line.product_id:
                raise UserError(_("RFQ Line must have a product: %s") % line.name)

            order_lines.append(Command.create({
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.name,
                'product_qty': line.qty,
                'price_unit': line.price_unit,
                'product_uom': line.uom_id.id,
                'analytic_distribution': line.analytic_distribution,
            }))

        po_vals['order_line'] = order_lines

        purchase_order = self.env['purchase.order'].create(po_vals)
        # purchase_order.button_confirm()
        # Attach PO to tender bid
        self.purchase_id = purchase_order.id
        self.tender_rfq_id.purchase_id = purchase_order.id

        # Log chatter message
        self.message_post(
            body=_("Purchase Order %s has been created for this awarded bid.")
                 % purchase_order.name
        )

    def action_open_purchase(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Order"),
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'views': [(False, 'form')],
            'res_id': self.purchase_id.id,
        }

    def _validate_tender_checklist(self):
        for record in self.tender_checklist_ids:
            if not record.is_checked:
                raise ValidationError(_('One or more Tender checklist record is not checked'))

    @api.constrains('tender_rfq_id', 'bid_user_id')
    def _check_unique_bid_user_per_tender(self):
        for rec in self:
            if not rec.tender_rfq_id or not rec.bid_user_id:
                continue
            duplicates = self.search([
                ('tender_rfq_id', '=', rec.tender_rfq_id.id),
                ('bid_user_id', '=', rec.bid_user_id.id),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id)
            ], limit=1)
            if duplicates:
                raise ValidationError(_(
                    "User '%s' already has a bid submitted for tender '%s'."
                ) % (rec.bid_user_id.name, rec.tender_rfq_id.title or rec.tender_rfq_id.name))

    @api.constrains('manual_currency_rate')
    def _check_currency_rate(self):
        """Ensure the currency rate is strictly positive when record's currency differs from company currency."""
        for rec in self:
            if (
                    rec.currency_id
                    and rec.company_id
                    and rec.currency_id != rec.company_currency_id
                    and rec.manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        self.manual_currency_rate = self.expected_currency_rate

    def refresh_currency_rate(self):
        for so in self:
            so.manual_currency_rate = so.expected_currency_rate

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_expected_currency_rate(self):
        for so in self:
            if so.currency_id:
                so.expected_currency_rate = so.env['res.currency']._get_conversion_rate(
                    from_currency=so.company_currency_id,
                    to_currency=so.currency_id,
                    company=so.company_id,
                    date=fields.Date.context_today(self),
                )
            else:
                so.expected_currency_rate = 1

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    @api.depends(
        'technical_evaluation_checklist_ids.score',
        'commercial_evaluation_checklist_ids.score',
        'technical_score_weight',
        'commercial_score_weight'
    )
    def _compute_scores(self):
        """Compute total scores (technical, commercial, and weighted total)."""
        for rec in self:
            tech_sum = sum(rec.technical_evaluation_checklist_ids.mapped('score'))
            comm_sum = sum(rec.commercial_evaluation_checklist_ids.mapped('score'))

            rec.total_technical_score = tech_sum
            rec.total_commercial_score = comm_sum

            rec.total_score = (
                    (tech_sum * rec.technical_score_weight / 100.0)
                    + (comm_sum * rec.commercial_score_weight / 100.0)
            )

    @api.depends('bid_user_id')
    def _compute_partner_id(self):
        for rec in self:
            rec.partner_id = rec.bid_user_id.partner_id if rec.bid_user_id else False

    @api.depends('partner_id')
    def _compute_bid_user_id(self):
        for rec in self:
            # Set user based on partner
            rec.bid_user_id = rec.partner_id.user_ids[:1] if rec.partner_id else False

    def _inverse_partner_id(self):
        for rec in self:
            # When partner is set manually, update user
            rec.bid_user_id = rec.partner_id.user_ids[:1] if rec.partner_id else False

    def _inverse_bid_user_id(self):
        for rec in self:
            # When user is set manually, update partner
            rec.partner_id = rec.bid_user_id.partner_id if rec.bid_user_id else False

    def generate_evaluation_checklist(self):
        if not self.technical_evaluation_checklist_id:
            raise ValidationError(_("Technical Evaluation Checklist is required"))
        if not self.commercial_evaluation_checklist_id:
            raise ValidationError(_("Commercial Evaluation Checklist is required"))
        self.technical_evaluation_checklist_ids = [Command.clear()] + [
            Command.create({
                'sequence': idx + 1,
                'name': rec.name,
                'evaluation_type': self.technical_evaluation_checklist_id.evaluation_type,
                'weight': rec.weight,
            }) for idx, rec in
            enumerate(self.technical_evaluation_checklist_id.checklist_conf_line_ids)
        ]
        self.commercial_evaluation_checklist_ids = [Command.clear()] + [
            Command.create({
                'sequence': idx + 1,
                'name': rec.name,
                'evaluation_type': self.commercial_evaluation_checklist_id.evaluation_type,
                'weight': rec.weight,
            }) for idx, rec in
            enumerate(self.commercial_evaluation_checklist_id.checklist_conf_line_ids)
        ]

    @api.constrains('partner_id', 'bid_user_id')
    def _constrains_partner_id(self):
        for record in self:
            if record.partner_id:
                if not record.partner_id.is_vendor:
                    raise ValidationError(
                        "The Partner must be Vendor be selected in this bid.")
                if record.partner_id.state != 'approved':
                    raise ValidationError(
                        "The Partner must be in 'Approved' state to be selected in this bid.")
                if record.partner_id.has_expired_documents:
                    raise ValidationError(
                        "You cannot choose a partner who has expired documents, Please update the expired documents.")
            else:
                raise ValidationError(_("A Valid Partner must be selected in this bid"))

    def _validate_rfq_line(self):
        for rec in self.tender_bid_rfq_line_ids:
            if rec.qty <= 0:
                raise ValidationError(_("RFQ Lines Qty must be greater than 0."))
            if rec.price_unit <= 0:
                raise ValidationError(_("RFQ Lines Price Unit must be greater than 0."))

    def action_bid_evaluated(self):
        self.ensure_one()
        for approval in self.tender_bid_approval_ids:
            if not approval.signature:
                raise ValidationError(_(
                    "All approvals from both Technical and Commercial sections "
                    "must be signed before this bid can be marked as evaluated."
                ))
        self.state = 'bid_evaluated'

    @api.onchange('tender_rfq_id')
    def _onchange_tender_rfq_id(self):
        self.tender_bid_rfq_line_ids = [Command.clear()]
        self.tender_bid_required_attachment_ids = [Command.clear()]

    def action_rfq_and_attachment_lines(self):
        self.ensure_one()
        write_vals = {}
        if not self.tender_bid_rfq_line_ids:
            write_vals['tender_bid_rfq_line_ids'] = [Command.create({
                'product_id': rec.product_id.id,
                'account_id': rec.account_id.id,
                'analytic_distribution': rec.analytic_distribution,
                'qty': 0,
                'required_qty': rec.qty,
                'price_unit': 0,
                'expected_price_unit': rec.price_unit,
            }) for rec in self.tender_rfq_id.tender_rfq_line_ids]
        if not self.tender_bid_required_attachment_ids and self.tender_rfq_id.tender_required_attachment_ids:
            write_vals['tender_bid_required_attachment_ids'] = [Command.create({
                'sequence': idx + 1,
                'name': rec.name,
            }) for idx, rec in enumerate(self.tender_rfq_id.tender_required_attachment_ids)]
        if write_vals:
            self.write(write_vals)

    def _validate_tender_bid_required_attachment(self):
        self.ensure_one()
        for rec in self.tender_bid_required_attachment_ids:
            if not rec.attachment_id:
                raise ValidationError(
                    _("Some lines in the Required Attachment doesn't have an attachment"))

    def action_pre_qualify(self):
        self.ensure_one()
        self._validate_tender_bid_required_attachment()
        self._validate_rfq_line()
        self.action_generate_checklist()
        self.state = 'pre_qualify'

    def action_reject(self):
        self.ensure_one()
        self._validate_tender_checklist()
        self.state = 'rejected'

    def generate_sign_list(self):
        commands = [Command.clear()]
        sequence = 1

        # Technical approvers
        for user in self.technical_user_ids:
            commands.append(Command.create({
                'sequence': sequence,
                'user_id': user.id,
                'request_type': 'approve',
                'parent_state_at_request': 'Evaluated',
                'signature': '',
            }))
            sequence += 1

        # Commercial approvers
        for user in self.commercial_user_ids:
            commands.append(Command.create({
                'sequence': sequence,
                'user_id': user.id,
                'request_type': 'approve',
                'parent_state_at_request': 'Evaluated',
                'signature': '',
                'evaluation_type': 'commercial',
            }))
            sequence += 1

        self.tender_bid_approval_ids = commands

    def action_move_to_evaluate(self):
        self.ensure_one()
        self._validate_tender_checklist()
        self.generate_evaluation_checklist()
        self.generate_sign_list()
        self._validate_rfq_line()
        self.state = 'evaluation'

    def _action_send_awarded_mail(self):
        """Send Awarded notification to vendors. Handles multiple tender records."""
        template = self.env.ref('kaz_vendor_management.mail_template_tender_awarded',
                                raise_if_not_found=False)
        if not template:
            raise UserError(_("Mail template not found. Please contact Administrator."))

        for bid in self:
            partner = bid.partner_id
            if not partner:
                raise UserError(_("No vendors found to notify for tender '%s'." % bid.name))
            if not partner.email:
                continue
            email_values = {
                'email_to': partner.email
            }
            context = {
                'partner': partner.name,
            }
            template.with_context(context).send_mail(bid.id, email_values=email_values,
                                                     force_send=True)
        return True

    def action_generate_checklist(self):
        """Generate checklists for tender RFQ documents"""
        self.ensure_one()
        checklists = self.env['tender.checklist.conf'].search(
            ['|', ('partner_category_ids', '=', False),
             ('partner_category_ids', 'in', self.tender_rfq_id.partner_category_ids.ids)])
        self.tender_checklist_ids = [Command.clear()] + [
            Command.create({
                'sequence': idx + 1,
                'name': rec.name,
            }) for idx, rec in enumerate(checklists)
        ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('tender.bid') or 'New'
        res = super().create(vals_list)
        res._check_max_bids_and_close_tender()
        return res

    def _check_max_bids_and_close_tender(self):
        """
        Automatically closes tenders that have reached the maximum number of allowed bids.

        This method iterates through all related Tender RFQs and checks their associated
        Purchase Requisition configuration. If the number of submitted bids for a tender
        is greater than or equal to the configured `max_bids`, the tender is closed by
        triggering `action_tender_close()`.

        Behavior:
            - Fetches all `tender_rfq_id` records linked to the current recordset.
            - Retrieves related requisition rules (max_bids).
            - Compares the current bid count with max_bids.
            - Closes the tender automatically when the limit is reached.

        Intended to be used in automated checks (cron or triggers) ensuring tenders are
        closed at the correct time without manual intervention.
        """
        tender_rfq_ids = self.mapped('tender_rfq_id')
        for tender in tender_rfq_ids:
            requisition = tender.purchase_requisition_id
            if requisition:
                max_bids = requisition.requisition_type_id.max_bids
                number_of_bids = tender.bid_count
                if number_of_bids >= max_bids > 0:
                    # tender.action_tender_close()
                    if tender.is_portal:
                        raise ValidationError(
                            _("Sorry Your submission was not registered, The maximum number of bids has reached. The tender will be closed soon.")
                        )
                    raise ValidationError(
                        _("Maximum number of bids (%d) reached. The tender must be closed.") % max_bids
                    )
