from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RelatedPartyEntries(models.Model):
    _name = 'related.party.entries'
    _inherit = "mail.thread", "mail.activity.mixin"
    _description = "Related Party Entries"

    name = fields.Char(default="New",
                       copy=False,
                       readonly=True)

    type = fields.Selection([
        ("lending", "Lending"),
        ("investment", "Investment"),
        ("cost_allocation", "Cost Allocation"),
    ], default='lending', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
    ],
        default='draft',
        tracking=True)

    # journal _ids

    journal_entry_ids = fields.Many2many('account.move')

    # Parent Company

    parent_company_id = fields.Many2one('res.company',
                                        default=lambda self: self.env.company.id)
    parent_currency_id = fields.Many2one('res.currency',
                                         related='parent_company_id.currency_id')

    parent_company_miscellaneous_journal_id = fields.Many2one(
        'account.journal',
        string="Miscellaneous Journal of Parent Company",
        domain="[('company_id', '=', parent_company_id), ('type', 'in', ['general'])]")
    parent_company_expense_account_id = fields.Many2one(
        'account.account',
        string="Expense Account of Parent Company",
        domain="[('company_ids', 'in', [parent_company_id]), ('account_type', '=', 'expense')]")

    related_subsidiary_company_account_id = fields.Many2one(
        'account.account',
        domain="[('company_ids', 'in', [parent_company_id]), ('is_related_party', '=', True), ('related_company_id', '=', subsidiary_company_id)]",
        string="Related Account of Subsidiary Company")

    related_party_parent_journal_id = fields.Many2one(
        'account.journal',
        domain="[('company_id', '=', parent_company_id), ('type', 'in', ['bank', 'cash'])]",
        string="Related Party Journal of Parent Company",
        default=lambda x: x.parent_company_id.related_party_journal_id.id)

    @api.onchange('parent_company_id')
    def onchange_parent_company_id(self):
        self.related_party_parent_journal_id = self.parent_company_id.related_party_journal_id.id

    #     Subsidiary Company

    subsidiary_company_id = fields.Many2one('res.company')
    related_parent_company_account_id = fields.Many2one(
        'account.account',
        domain="[('company_ids', 'in', [subsidiary_company_id]), ('is_related_party', '=', True), ('related_company_id', '=', parent_company_id)]",
        string="Related Account of Parent Company")
    related_party_subsidiary_journal_id = fields.Many2one(
        'account.journal',
        domain="[('company_id', '=', subsidiary_company_id), ('type', 'in', ['bank', 'cash'])]",
        string="Related Party Journal of Subsidiary Company",
        default=lambda x: x.subsidiary_company_id.related_party_journal_id.id)

    @api.onchange('subsidiary_company_id')
    def onchange_subsidiary_company_id(self):
        self.related_party_subsidiary_journal_id = self.subsidiary_company_id.related_party_journal_id.id

    amount = fields.Float()
    default_company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company.id)

    cost_allocation_ids = fields.One2many(
        'cost.allocation.company',
        'related_party_entry_id'
    )

    @api.constrains('cost_allocation_ids')
    def constrains_cost_allocation(self):
        if self.type == 'cost_allocation':
            if sum(self.cost_allocation_ids.mapped('percentage')) > 100:
                raise ValidationError('Max Cost Allocation should be 100.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code(
                'kaz.related.party.entry.seq')
            vals.update({
                'name': name
            })
            vals['name'] = name
        return super().create(vals_list)

    def submit_for_approval(self):
        self.state = 'pending'

    def action_confirm(self):
        amount = self.amount
        if self.type in ['lending', 'investment']:
            debit_line_parent = {
                'account_id': self.related_subsidiary_company_account_id.id,
                'debit': amount}
            credit_line_parent = {
                'account_id': self.related_party_parent_journal_id.default_account_id.id,
                'credit': amount}
            parent_move = self.env['account.move'].create({
                'move_type': 'entry',
                'company_id': self.parent_company_id.id,
                'date': fields.Date.today(),
                'ref': self.name,
                'journal_id': self.related_party_parent_journal_id.id,
                'line_ids': [(0, 0, debit_line_parent), (0, 0, credit_line_parent)],
            })

            debit_line_subsidiary = {
                'account_id': self.related_party_subsidiary_journal_id.default_account_id.id,
                'debit': amount}
            credit_line_subsidiary = {
                'account_id': self.related_parent_company_account_id.id,
                'credit': amount}
            subsidiary_move = self.env['account.move'].create({
                'move_type': 'entry',
                'company_id': self.subsidiary_company_id.id,
                'date': fields.Date.today(),
                'ref': self.name,
                'journal_id': self.related_party_subsidiary_journal_id.id,
                'line_ids': [(0, 0, debit_line_subsidiary), (0, 0, credit_line_subsidiary)],
            })
            self.write({
                'journal_entry_ids': [(4, parent_move.id), (4, subsidiary_move.id)],
                'state': 'confirmed'
            })
        elif self.type == 'cost_allocation':
            journal_ids = []
            for line in self.cost_allocation_ids:
                # In Parent
                company = self.parent_company_id
                amount = (self.amount * line.percentage) / 100
                debit_related_account_in_parent_to_child = line.account_child_in_parent_id
                credit_expense_account_of_parent = self.parent_company_expense_account_id
                journal = self.parent_company_miscellaneous_journal_id

                debit_lines_parent = {
                    'account_id': debit_related_account_in_parent_to_child.id,
                    'debit': amount
                }
                credit_lines_parent = {
                    'account_id': credit_expense_account_of_parent.id,
                    'credit': amount
                }
                parent_company_id = company

                parent_journal = journal

                parent_move = self.env['account.move'].sudo().create({
                    'move_type': 'entry',
                    'company_id': parent_company_id.id,
                    'date': fields.Date.today(),
                    'ref': self.name,
                    'journal_id': parent_journal.id,
                    'line_ids': [(0, 0, debit_lines_parent),
                                 (0, 0, credit_lines_parent)],
                })

                journal_ids.append(parent_move.id)

                # In Child
                child_company = line.company_id
                amount_child = (self.amount * line.percentage) / 100
                debit_expense_or_cost_of_child = line.debit_account_id
                credit_related_account_of_parent_in_child = line.account_parent_in_child_id
                journal_child = line.miscellaneous_journal_id

                debit_lines_child = {
                    'account_id': debit_expense_or_cost_of_child.id,
                    'debit': amount_child
                }
                credit_lines_child = {
                    'account_id': credit_related_account_of_parent_in_child.id,
                    'credit': amount_child
                }

                child_move = self.env['account.move'].sudo().create({
                    'move_type': 'entry',
                    'company_id': child_company.id,
                    'date': fields.Date.today(),
                    'ref': self.name,
                    'journal_id': journal_child.id,
                    'line_ids': [(0, 0, debit_lines_child),
                                 (0, 0, credit_lines_child)],
                })

                journal_ids.append(child_move.id)

            self.write({
                'journal_entry_ids': [(4, j_id) for j_id in journal_ids],
                'state': 'confirmed'
            })

    def show_journal_entry_ids(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.journal_entry_ids.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_cancel(self):
        self.write({
            'state': 'canceled'
        })

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'canceled']:
                raise ValidationError(
                    "Cannot delete Party Entries which"
                    " are not in draft/ canceled state.")


class CostAllocationCompany(models.Model):
    _name = 'cost.allocation.company'
    _description = "Cost Allocation Company"

    related_party_entry_id = fields.Many2one('related.party.entries')
    parent_company_id = fields.Many2one(
        'res.company',
        related='related_party_entry_id.parent_company_id')

    company_id = fields.Many2one('res.company',
                                 required=True)
    total_amount = fields.Float(
        related='related_party_entry_id.amount',
        store=True)
    percentage = fields.Float(string="Percentage (%)",

                              required=True)

    amount = fields.Float(string="Amount",
                          compute='_compute_amount',
                          inverse='_inverse_amount',
                          readonly=False,
                          store=True,)

    @api.depends('percentage',
                 'total_amount')
    def _compute_amount(self):
        for rec in self:
            if rec.total_amount:
                rec.amount = (rec.total_amount * rec.percentage) / 100.0
            else:
                rec.amount = 0.0

    def _inverse_amount(self):
        for rec in self:
            if rec.total_amount:
                rec.percentage = (rec.amount / rec.total_amount) * 100.0
            else:
                rec.percentage = 0.0

    debit_account_id = fields.Many2one(
        'account.account',
        string="Shared Service Expense",
        required=True,
        domain="[('company_ids', 'in', [company_id]), ('account_type', '=', 'expense')]")

    account_child_in_parent_id = fields.Many2one(
        'account.account',
        string="Account of Child in Parent",
        required=True,
        domain="[('company_ids', 'in', [parent_company_id]),('is_related_party', '=', True), ('related_company_id', '=', company_id)]")
    account_parent_in_child_id = fields.Many2one(
        'account.account',
        string="Account of Parent in Child",
        required=True,
        domain="[('company_ids', 'in', [company_id]),('is_related_party', '=', True), ('related_company_id', '=', parent_company_id)]")

    miscellaneous_journal_id = fields.Many2one(
        'account.journal',
        domain="[('company_id', '=', company_id), ('type', 'in', ['general'])]",
        required=True,
        string="Miscellaneous Journal of Child Company")
