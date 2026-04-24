# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class EmployeeOvertime(models.Model):
    """
        Model to manage employee overtime request lifecycle including:
        - Draft creation by employee
        - Multi-level approvals: Line Manager, HR, and Director
        - Rejection and cancellation handling
        - Tracks associated employee details and purpose of overtime
        - Integrated with chatter and activity mixin for communication
        """
    _name = 'employee.overtime'
    _description = 'Employee Overtime'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_default_employee(self):
        """
                Fetch the default employee associated with the current user
                if such an employee exists in the current company.

                :return: ID of hr.employee or empty list
                """
        emp = self.env['hr.employee'].sudo().search([(
            'user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)],
            limit=1)
        return emp.id if emp else []

    def get_default_domain(self):
        """
                Return a domain restricting employee selection to the logged-in
                user's department if they are a Line Manager, but not HR or Director.

                :return: domain tuple for employee_id field
                """
        user = self.env.user
        if user.has_group('kaz_employee_overtime.group_line_manager') \
                and not user.has_group('kaz_employee_overtime.group_hr_person') \
                and not user.has_group('kaz_employee_overtime.group_director'):
            return [('department_id', '=', user.employee_id.department_id.id)]
        else:
            return []

    employee_id = fields.Many2one('hr.employee', string="Employee",
                                  default=get_default_employee,
                                  domain=get_default_domain,
                                  required=True, tracking=True)
    job_id = fields.Many2one(related="employee_id.job_id")
    grade_id = fields.Many2one(related="employee_id.grade_id")
    department_id = fields.Many2one(related="employee_id.department_id")
    purpose_overtime = fields.Text(string="Purpose of Overtime")
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('line_manager_approval', 'Line Manager Approval'),
                              ('hr_approval', 'HR Approval'),
                              ('director_approval', 'Director Approval'),
                              ('approved', 'Approved'),
                              ('rejected', 'Rejected'),
                              ('canceled', 'Canceled')],
                             default='draft',
                             tracking=True)

    def action_send_for_line_manager_approval(self):
        """
               Submit the overtime request for Line Manager's approval.
               Transition state from 'draft' to 'line_manager_approval'.
               """
        self.write({'state': 'line_manager_approval'})

    def action_send_for_hr_approval(self):
        """
                Submit the overtime request to HR after Line Manager approval.
                Transition state from 'line_manager_approval' to 'hr_approval'.
                """
        self.write({'state': 'hr_approval'})

    def action_send_for_director(self):
        """
                Submit the overtime request to Director for final approval.
                Transition state from 'hr_approval' to 'director_approval'.
                """
        self.write({'state': 'director_approval'})

    def action_approve(self):
        """
                Approve the overtime request at the Director level.
                Final state transition to 'approved'.
                """
        self.write({'state': 'approved'})

    def action_reject_line_manager(self):
        """
                Reject the request during Line Manager review.
                Transition state to 'rejected'.
                """
        self.write({'state': 'rejected'})

    def action_reject_hr(self):
        """
                Reject the request during HR review.
                Transition state to 'rejected'.
                """
        self.write({'state': 'rejected'})

    def action_reject_director(self):
        """
                Reject the request during Director review.
                Transition state to 'rejected'.
                """
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """
                Cancel the overtime request. Allowed by the requestor at any stage.
                Transition state to 'canceled'.
                """
        self.write({'state': 'canceled'})

    def unlink(self):
        """
                Override deletion to restrict deleting requests that are not
                in 'draft' or 'canceled' states.

                :raises UserError: If trying to delete request in non-deletable state
                :return: Super call to unlink
                """
        for rec in self:
            if rec.state not in ('draft', 'canceled'):
                raise UserError(
                    _('You cannot delete an overtime'
                      ' request which is not in draft or cancelled state'))
        return super().unlink()
