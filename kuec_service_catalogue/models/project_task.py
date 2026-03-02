# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProjectTaskWink(models.Model):
    _inherit = 'project.task'

    wink_employee_ids = fields.Many2many(
        'kuec.employee.directory',
        'project_task_employee_rel',
        'task_id',
        'employee_id',
        string='Employees',
        help='Employees linked to this task (from WINK request or added in backend).',
    )
    document_submission_ids = fields.One2many(
        'kuec.document.submission',
        'task_id',
        string='Document Submissions',
        help='Compliance documents linked to this task.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if not task.sale_order_id or not task.sale_order_id.wink_is_portal_request:
                continue
            order = task.sale_order_id
            # WF-BND-001: prefer employees on activated line (sale_line.wink_selected_employee_ids), else entitlement, else order
            employee_ids = []
            sale_line = getattr(task, 'sale_line_id', None)
            if sale_line and getattr(sale_line, 'wink_entitlement_id', None):
                if getattr(sale_line, 'wink_selected_employee_ids', None) and sale_line.wink_selected_employee_ids:
                    employee_ids = sale_line.wink_selected_employee_ids.ids
                if not employee_ids:
                    employee_ids = sale_line.wink_entitlement_id.wink_selected_employee_ids.ids
            if not employee_ids:
                employee_ids = order.wink_selected_employee_ids.ids
            if employee_ids:
                task.wink_employee_ids = [(6, 0, employee_ids)]
            # Link order documents to this task when order has a single task (standalone)
            if task.project_id:
                order_tasks = self.search([
                    ('sale_order_id', '=', order.id),
                    ('project_id', '=', task.project_id.id),
                ])
                if len(order_tasks) <= 1:
                    order.document_submission_ids.write({'task_id': task.id})
        return tasks

    def write(self, vals):
        if 'stage_id' in vals:
            new_stage = self.env['project.task.type'].browse(vals['stage_id'])
            if not new_stage.exists():
                return super().write(vals)

            for task in self:
                # If we are changing stages, check compliance on WINK portal requests
                if task.sale_order_id and task.sale_order_id.wink_is_portal_request:
                    old_stage = task.stage_id
                    if not old_stage:
                        continue
                    # If moving to a new stage (from the very first stage 'sequence 1-10' typically 'New')
                    if (old_stage.id != new_stage.id
                            and old_stage.sequence <= 10
                            and new_stage.sequence > old_stage.sequence):
                        # WF-BND-003: for activated bundle lines, check docs for that line's product only
                        order = task.sale_order_id
                        all_approved = True
                        pending_names = []
                        sale_line = getattr(task, 'sale_line_id', None)
                        if sale_line and getattr(sale_line, 'wink_entitlement_id', None):
                            product_tmpl = sale_line.product_id.product_tmpl_id
                            all_approved, pending_names = order._wink_required_docs_approved_for_product(product_tmpl)
                        else:
                            # ISSUE-003: pending is always a list of document name strings.
                            all_approved, pending_names = order._wink_all_required_docs_approved()
                        if not all_approved:
                            raise UserError(_(
                                "Compliance Hard-Gate: You cannot move this task out of the 'New' stage because the customer has missing or unapproved documents: %s"
                            ) % ", ".join(pending_names))
        return super().write(vals)
