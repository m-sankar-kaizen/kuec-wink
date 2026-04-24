# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ActingDelegation(models.Model):
    _name = 'acting.delegation'
    _description = 'Acting Delegation During Time Off'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', default=lambda self: _('New'), copy=False)
    leave_id = fields.Many2one('hr.leave', string='Time Off Request', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    acting_user_id = fields.Many2one('res.users', string='Acting User', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    date_start = fields.Datetime(string='Start', required=True)
    date_end = fields.Datetime(string='End', required=True)

    group_ids = fields.Many2many(
        'res.groups',
        'acting_delegation_group_rel',
        'delegation_id',
        'group_id',
        string='Delegated Groups',
        help='Groups to temporarily grant to the acting user'
    )
    allowed_group_ids = fields.Many2many(
        'res.groups', string='Allowed Source Groups', compute='_compute_allowed_groups', store=False,
        help='Only groups that the leave owner user already has'
    )
    granted_group_ids = fields.Many2many(
        'res.groups',
        'acting_delegation_granted_group_rel',
        'delegation_id',
        'group_id',
        string='Granted Groups (Audit)',
        readonly=True,
        help='Groups actually granted by this delegation to avoid removing pre-existing ones'
    )

    delegation_type = fields.Selection([
        ('ownership', 'Ownership (Full Transfer)'),
        ('notify', 'Notify Only'),
    ], string='Delegation Type', default='ownership', required=True, help='Ownership: grant selected groups. Notify Only: no groups, only notifications.')

    hierarchy_required = fields.Boolean(string='Hierarchy Required', default=False)
    allowed_user_ids = fields.Many2many('res.users', string='Allowed Acting Users', compute='_compute_allowed_users', store=False)
    validation_type = fields.Selection([
        ('blocking', 'Blocking'),
        ('warning', 'Warning'),
    ], string='Validation Type', default='blocking')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    can_reactivate = fields.Boolean(string='Can Reactivate', compute='_compute_can_reactivate', store=False)

    justification = fields.Text(string='Justification')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError(_('End date must be after start date.'))
            if rec.leave_id:
                # Support Odoo 18 field names by checking available attrs
                leave_start = getattr(rec.leave_id, 'request_date_from', False) or getattr(rec.leave_id, 'date_from', False)
                leave_end = getattr(rec.leave_id, 'request_date_to', False) or getattr(rec.leave_id, 'date_to', False)
                # Normalize to dates to avoid datetime vs date comparison issues
                if leave_start and leave_end:
                    from datetime import datetime, date
                    def to_date(v):
                        if isinstance(v, datetime):
                            return v.date()
                        if isinstance(v, date):
                            return v
                        return False
                    ls = to_date(leave_start)
                    le = to_date(leave_end)
                    ds = rec.date_start.date() if rec.date_start else False
                    de = rec.date_end.date() if rec.date_end else False
                    if ls and le and ds and de and (ds < ls or de > le):
                        raise ValidationError(_('Delegation period must be within the leave period.'))

    def _compute_hierarchy_required(self):
        for rec in self:
            # fixed threshold in days (no system parameters)
            threshold = 5
            # compute working days approx (calendar-aware can be added)
            days = 0
            if rec.leave_id:
                leave_start = getattr(rec.leave_id, 'request_date_from', False) or getattr(rec.leave_id, 'date_from', False)
                leave_end = getattr(rec.leave_id, 'request_date_to', False) or getattr(rec.leave_id, 'date_to', False)
                if leave_start and leave_end:
                    from datetime import datetime, date
                    def to_date(v):
                        if isinstance(v, datetime):
                            return v.date()
                        if isinstance(v, date):
                            return v
                        return False
                    ls = to_date(leave_start)
                    le = to_date(leave_end)
                    if ls and le:
                        days = (le - ls).days + 1
            rec.hierarchy_required = days >= threshold

    @api.depends('employee_id', 'hierarchy_required')
    def _compute_allowed_users(self):
        for rec in self:
            users_model = self.env['res.users']
            if not rec.employee_id:
                rec.allowed_user_ids = users_model
                continue
            # Build candidate employees per hierarchy
            emp = rec.employee_id
            emp_model = self.env['hr.employee']
            domain = [('company_id', '=', emp.company_id.id), ('active', '=', True), ('id', '!=', emp.id)]
            candidates = emp_model.search(domain)
            if rec.hierarchy_required:
                subs = emp.child_ids
                sup = emp.parent_id
                sup2 = emp.parent_id.parent_id if emp.parent_id else emp_model
                peers = candidates.filtered(lambda e: e.department_id == emp.department_id and e.job_id == emp.job_id)
                allowed_emps = (subs | peers | (sup if sup else emp_model) | (sup2 if sup2 else emp_model))
            else:
                allowed_emps = candidates
            # Map allowed employees to users in same company
            user_candidates = users_model.search([
                ('company_id', '=', rec.company_id.id),
                ('employee_ids', 'in', allowed_emps.ids)
            ])
            rec.allowed_user_ids = user_candidates

    def _is_in_allowed_hierarchy(self):
        emp = self.employee_id
        acting_user = self.acting_user_id
        acting = acting_user.employee_ids[:1] if acting_user and acting_user.employee_ids else False
        if not emp or not acting:
            return False
        # Immediate Subordinate
        if acting in emp.child_ids:
            return True
        # Immediate Supervisor
        if emp.parent_id and acting == emp.parent_id:
            return True
        # Supervisor's Supervisor
        if emp.parent_id and emp.parent_id.parent_id and acting == emp.parent_id.parent_id:
            return True
        # Equivalent Peer: same department and job
        if acting.department_id == emp.department_id and acting.job_id == emp.job_id:
            return True
        return False

    @api.constrains('acting_user_id')
    def _check_hierarchy(self):
        for rec in self:
            rec._compute_hierarchy_required()
            if rec.hierarchy_required and not rec._is_in_allowed_hierarchy():
                if rec.validation_type == 'blocking':
                    raise ValidationError(_('Selected user is not eligible to act on your behalf. Please choose someone from the defined hierarchy.'))
                else:
                    rec.leave_id.message_post(body=_('Warning: It is recommended to choose an acting replacement from the defined hierarchy.'))

    @api.depends('employee_id')
    def _compute_allowed_groups(self):
        for rec in self:
            groups = self.env['res.groups']
            if rec.employee_id and rec.employee_id.user_id:
                groups = rec.employee_id.user_id.groups_id
            rec.allowed_group_ids = groups

    @api.constrains('acting_user_id')
    def _check_internal_user(self):
        for rec in self:
            if rec.acting_user_id and rec.acting_user_id.share:
                raise ValidationError(_('Acting user must be an internal user (not portal/public).'))

    def action_activate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft delegations can be activated.'))
            if rec.delegation_type == 'ownership' and not rec.group_ids:
                raise UserError(_('Please select at least one group to delegate.'))
            # Grant groups
            user = rec.acting_user_id
            if not user:
                raise UserError(_('Please select an acting user.'))
            # Ensure selected groups are a subset of source employee user's groups
            source_groups = rec.employee_id.user_id.groups_id if rec.employee_id and rec.employee_id.user_id else self.env['res.groups']
            invalid = rec.group_ids - source_groups
            if invalid:
                raise ValidationError(_('You can only delegate groups already owned by the leave owner. Invalid: %s') % (", ".join(invalid.mapped('name'))))
            if rec.delegation_type == 'ownership':
                current = user.groups_id
                to_add = (rec.group_ids & source_groups) - current
                if to_add:
                    user.sudo().write({'groups_id': [(4, g.id) for g in to_add]})
                    rec.granted_group_ids = [(6, 0, to_add.ids)]
            rec.state = 'active'
            rec.leave_id.message_post(body=_('Acting delegation activated for %s from %s to %s.') % (user.name, rec.date_start, rec.date_end))
            # Notify acting user and HR managers
            hr_managers = self.env.ref('hr.group_hr_manager').users
            partners = (hr_managers.mapped('partner_id') | user.partner_id)
            for p in partners:
                rec.activity_schedule('mail.mail_activity_data_todo', user_id=p.user_ids[:1].id if p.user_ids else False, note=_('You have acting responsibilities from %s to %s.') % (rec.date_start, rec.date_end))

    def _revoke_groups(self):
        for rec in self:
            user = rec.acting_user_id
            if user:
                # Prefer removing only the groups granted by this delegation; fallback to intersection
                to_remove = rec.granted_group_ids
                if not to_remove:
                    to_remove = rec.group_ids & user.groups_id
                if to_remove:
                    user.sudo().write({'groups_id': [(3, g.id) for g in to_remove]})
                rec.granted_group_ids = [(6, 0, [])]

    def action_revoke(self):
        for rec in self:
            if rec.state != 'active':
                raise UserError(_('Only active delegations can be revoked.'))
            rec._revoke_groups()
            rec.state = 'revoked'
            msg = _('Acting delegation revoked.')
            if rec.justification:
                msg = _('Acting delegation revoked. Reason: %s') % (rec.justification)
            rec.leave_id.message_post(body=msg)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_('Delegation is already cancelled.'))
            rec._revoke_groups()
            rec.state = 'cancelled'
            msg = _('Acting delegation cancelled.')
            if rec.justification:
                msg = _('Acting delegation cancelled. Reason: %s') % (rec.justification)
            rec.leave_id.message_post(body=msg)

    def _compute_can_reactivate(self):
        now = fields.Datetime.now()
        for rec in self:
            in_window = bool(rec.date_start and rec.date_end and rec.date_start <= now <= rec.date_end)
            # Show re-activate only when revoked and within leave window
            rec.can_reactivate = in_window and rec.state == 'revoked'

    def action_reactivate(self):
        for rec in self:
            rec._compute_can_reactivate()
            if not rec.can_reactivate:
                raise UserError(_('Delegation cannot be re-activated now. It must be within the leave period and be in Revoked state.'))
            # re-grant groups (subset enforcement already in activation)
            if rec.delegation_type == 'ownership':
                user = rec.acting_user_id
                if not user:
                    raise UserError(_('Please select an acting user.'))
                source_groups = rec.employee_id.user_id.groups_id if rec.employee_id and rec.employee_id.user_id else self.env['res.groups']
                to_add = (rec.group_ids & source_groups) - user.groups_id
                if to_add:
                    user.sudo().write({'groups_id': [(4, g.id) for g in to_add]})
                    rec.granted_group_ids = [(6, 0, to_add.ids)]
            rec.state = 'active'
            # Prepare @user_id and group names for the message
            user_mention = '<span>@%s</span>' % rec.acting_user_id.id if rec.acting_user_id else ''
            group_names = ', '.join(rec.group_ids.mapped('name')) if rec.group_ids else 'No groups'
            rec.leave_id.message_post(
                body=_('Acting delegation re-activated for %(user)s. Groups: %(groups)s') % {
                    'user': user_mention,
                    'groups': group_names
                }
            )

    def cron_auto_revoke(self):
        now = fields.Datetime.now()
        records = self.search([('state', '=', 'active'), ('date_end', '<=', now)])
        for rec in records:
            rec._revoke_groups()
            rec.state = 'expired'
            rec.leave_id.message_post(body=_('Acting delegation expired and permissions revoked.'))

    @api.model
    def create(self, vals):
        # Ensure employee_id is set when created from hr.leave inline, using leave's employee
        if not vals.get('employee_id') and vals.get('leave_id'):
            leave = self.env['hr.leave'].browse(vals['leave_id'])
            if leave and leave.employee_id:
                vals['employee_id'] = leave.employee_id.id
            # also default company from leave/employee
            if not vals.get('company_id'):
                vals['company_id'] = (leave.company_id.id if leave and leave.company_id else self.env.company.id)
            # default delegation dates to leave dates when not provided
            if not vals.get('date_start'):
                vals['date_start'] = getattr(leave, 'request_date_from', False) or getattr(leave, 'date_from', False)
            if not vals.get('date_end'):
                vals['date_end'] = getattr(leave, 'request_date_to', False) or getattr(leave, 'date_to', False)
        # Only the user linked to the leave owner employee OR admin can create/edit delegation lines
        leave = None
        if vals.get('leave_id'):
            leave = self.env['hr.leave'].browse(vals['leave_id'])
        elif vals.get('employee_id'):
            leave = self.env['hr.leave'].search([('employee_id', '=', vals['employee_id'])], limit=1)
        is_admin = self.env.user.has_group('base.group_system')
        if leave and leave.employee_id and leave.employee_id.user_id and self.env.user != leave.employee_id.user_id and not is_admin:
            raise ValidationError(_('Only the user linked to the leave owner or an admin can manage delegation lines.'))
        return super().create(vals)

    def write(self, vals):
        is_admin = self.env.user.has_group('base.group_system')
        for rec in self:
            owner_user = rec.leave_id.employee_id.user_id if rec.leave_id and rec.leave_id.employee_id else False
            if owner_user and self.env.user != owner_user and not is_admin:
                raise ValidationError(_('Only the user linked to the leave owner or an admin can manage delegation lines.'))
        return super().write(vals)

    def unlink(self):
        is_admin = self.env.user.has_group('base.group_system')
        for rec in self:
            owner_user = rec.leave_id.employee_id.user_id if rec.leave_id and rec.leave_id.employee_id else False
            if owner_user and self.env.user != owner_user and not is_admin:
                raise ValidationError(_('Only the user linked to the leave owner or an admin can delete delegation lines.'))
        return super().unlink()
