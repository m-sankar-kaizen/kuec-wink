# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    company_code = fields.Selection(
        related='employee_company_id.company_code')

    delegate_choice = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Delegate Permissions?', default='no', tracking=True)
    delegation_ids = fields.One2many('acting.delegation', 'leave_id', string='Acting Delegations', readonly=False)
    acting_justification = fields.Text(string='Delegation Justification')

    def action_confirm(self):
        res = super().action_confirm()
        for leave in self:
            if leave.delegate_choice not in ('yes', 'no'):
                raise models.ValidationError(_('Please answer: Delegate permissions during leave?'))
            if leave.delegate_choice == 'yes':
                if not leave.delegation_ids:
                    raise models.ValidationError(_('Add at least one acting delegate with permissions.'))
                leave.message_post(body=_('Employee chose to delegate system permissions during leave.'))
                # Only validate structure here; activation occurs on approval
                default_start = getattr(leave, 'request_date_from', False) or getattr(leave, 'date_from', False)
                default_end = getattr(leave, 'request_date_to', False) or getattr(leave, 'date_to', False)
                for delegation in leave.delegation_ids:
                    # ensure required fields per type
                    if not delegation.acting_user_id:
                        raise models.ValidationError(_('Each delegation must have an acting user.'))
                    if delegation.delegation_type == 'ownership' and not delegation.group_ids:
                        raise models.ValidationError(_('Ownership delegations must include at least one group.'))
                    # pre-sync dates and validation type (final sync on approval)
                    delegation.write({
                        'date_start': delegation.date_start or default_start,
                        'date_end': delegation.date_end or default_end,
                    })
            else:
                leave.message_post(body=_('Employee chose not to delegate system permissions during leave.'))
                # Warn in red if leave duration exceeds threshold and no delegation lines
                threshold = int(leave.env['ir.config_parameter'].sudo().get_param('hr_acting_delegation.threshold_days', default='5'))
                start = getattr(leave, 'request_date_from', False) or getattr(leave, 'date_from', False)
                end = getattr(leave, 'request_date_to', False) or getattr(leave, 'date_to', False)
                from datetime import datetime, date
                def to_date(v):
                    if isinstance(v, datetime):
                        return v.date()
                    if isinstance(v, date):
                        return v
                    return False
                if start and end:
                    ds = to_date(start)
                    de = to_date(end)
                    if ds and de:
                        days = (de - ds).days + 1
                        if days >= threshold:
                            leave.message_post(body='<span style="color: red;">Warning: Acting delegation is recommended for leaves of %s days or more.</span>' % days)
        return res

    def _activate_delegations_on_approval(self):
        for leave in self:
            if leave.delegate_choice != 'yes':
                continue
            # Activate only when fully approved (final state)
            if getattr(leave, 'state', None) != 'validate':
                continue
            default_start = getattr(leave, 'request_date_from', False) or getattr(leave, 'date_from', False)
            default_end = getattr(leave, 'request_date_to', False) or getattr(leave, 'date_to', False)
            for delegation in leave.delegation_ids:
                # sync dates to leave window if missing
                updates = {}
                if not delegation.date_start:
                    updates['date_start'] = default_start
                if not delegation.date_end:
                    updates['date_end'] = default_end
                if updates:
                    delegation.write(updates)
                if delegation.state == 'draft':
                    delegation.action_activate()

    def action_validate(self, *args, **kwargs):
        res = super().action_validate(*args, **kwargs)
        self._activate_delegations_on_approval()
        return res

    # Some configurations use a one-step approval API
    def action_approve(self):
        res = super().action_approve()
        self._activate_delegations_on_approval()
        return res

    # Auto-cancel delegations when leave is reset/refused
    def _cancel_delegations(self, reason):
        for leave in self:
            for delegation in leave.delegation_ids.filtered(lambda d: d.state in ('draft','active','revoked')):
                delegation.write({'justification': reason})
                delegation.action_cancel()

    def _reset_delegations_to_draft(self):
        for leave in self:
            for delegation in leave.delegation_ids:
                # revoke any granted groups and reset to draft for re-run
                if delegation.state == 'active':
                    delegation._revoke_groups()
                delegation.write({'state': 'draft', 'justification': _('Leave reset to draft: restarting delegation cycle')})

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            if vals['state'] in ('refuse', 'cancel'):
                self._cancel_delegations(_('Leave set to %s: auto-cancelling delegations') % vals['state'])
            elif vals['state'] in ('draft', 'confirm'):
                self._reset_delegations_to_draft()
        return res

    def action_draft(self):
        res = super().action_draft()
        # Ensure delegations are reset when leave is reset to draft via the action
        self._reset_delegations_to_draft()
        return res

    def action_refuse(self):
        res = super().action_refuse()
        # Explicitly cancel delegations when leave is refused via action
        self._cancel_delegations(_('Leave refused: auto-cancelling delegations'))
        return res

    def action_cancel(self):
        res = super().action_cancel()
        # Explicitly cancel delegations when leave is cancelled via action
        self._cancel_delegations(_('Leave cancelled: auto-cancelling delegations'))
        return res

    def action_acting_revoke(self):
        for leave in self:
            for delegation in leave.delegation_ids.filtered(lambda d: d.state == 'active'):
                if not leave.acting_justification:
                    raise models.ValidationError(_('Justification is required to revoke delegation.'))
                delegation.write({'justification': leave.acting_justification})
                delegation.action_revoke()

    def action_acting_cancel(self):
        for leave in self:
            for delegation in leave.delegation_ids.filtered(lambda d: d.state in ('draft','active')):
                if not leave.acting_justification:
                    raise models.ValidationError(_('Justification is required to cancel delegation.'))
                delegation.write({'justification': leave.acting_justification})
                delegation.action_cancel()
