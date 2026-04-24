# -*- coding: utf-8 -*-
import logging
import warnings

from datetime import timedelta

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ApprovalBaseMixin(models.AbstractModel):
    """
    TO Be inherited by the parent record
    Mixin class to add a sequential approval workflow to any model.
    It provides fields for the approval state, signature, and the user who signed.
    """
    _name = 'approval.base.mixin'
    _description = 'Approval Base Mixin'

    def assign_activity(self, user_ids, summary, note, activity_type_xml_id=False):
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        for user in user_ids:
            self.activity_schedule(
                activity_type_id=self.env.ref(activity_type_xml_id).id,
                user_id=user.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today() + timedelta(days=3)
            )

    def _mark_activity_done(self, activity_type_xml_id=False):
        """Mark pending activities of a specific type as done."""
        self.ensure_one()
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    def _get_group_users(self, group_xml_id):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            raise ValidationError(f"The group '{group_xml_id}' does not exist.")
        if not group.users:
            raise ValidationError(f"No users are assigned to the group '{group.name}'.")
        return group.users

    def _validate_hod(self):
        """Validate that the current user is the assigned Department Head.

            Ensures that only the Department Head linked to the employee can
            perform approval actions on the evaluation form.

            Raises:
                UserError: If the current user is not the assigned Department Head.
        """
        self.ensure_one()
        manager = self._get_department_head()
        if manager:
            if manager.user_id:
                if self.env.user != manager.user_id:
                    raise UserError(
                        _("Only the Head of Department assigned to this employee can confirm this request."))
            else:
                raise UserError(_("The Department Head does not have an assigned user."))
        else:
            raise UserError(_("A Department Head is not assigned for this employee."))

    def _open_approve_reject_wizard(self, name, request_type, next_action):
        approval_model = self._approval_model
        approval_line = self._approval_line
        approval_state_field = self._approval_state
        additional_context = self._approval_context()
        self.ensure_one()

        # Warnings if not overridden
        if approval_model == '':
            warnings.warn(f"{self.__class__.__name__}._approval_model is not overridden",
                          UserWarning)
        if approval_line == []:
            warnings.warn(f"{self.__class__.__name__}._approval_line is not overridden",
                          UserWarning)
        if approval_state_field == '':
            warnings.warn(f"{self.__class__.__name__}._approval_state is not overridden",
                          UserWarning)
        elif approval_state_field not in self._fields:
            warnings.warn(
                f"{self.__class__.__name__}: field '{approval_state_field}' does not exist on the model",
                UserWarning)
        if additional_context == {}:
            warnings.warn(f"{self.__class__.__name__}._approval_context() is not overridden",
                          UserWarning)

        # Get the state value from the field
        state_at_request = self[
            approval_state_field].title() if approval_state_field in self._fields else ''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': approval_model,
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(approval_line) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': state_at_request,
                'default_next_action': next_action,
                **additional_context
            }
        }

    def _get_department_head(self):
        """To be overridden"""
        self.ensure_one()
        return None

    @property
    def _approval_model(self):
        """To be overridden
            eg: return 'approval.reject.mixin'
        """
        return ''

    @property
    def _approval_line(self):
        """To be overridden
            eg: return self.approval_line_ids
        """
        return []

    @property
    def _approval_state(self):
        """To be overridden
            eg: return 'state_field_name'
        """
        return 'kuec_approval_state'

    def _approval_context(self):
        """To be overridden
            eg: return {
                'default_your_field_id': self.id,
            }
        """
        self.ensure_one()
        return {}

    def _perform_action(self, state, user_ids=None, summary=None, note=None):
        self.ensure_one()
        self._mark_activity_done()
        self[self._approval_state] = state
        if user_ids:
            self.assign_activity(user_ids, summary, note)
