# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError, ValidationError


class PerformanceEvaluation(models.Model):
    _name = 'performance.evaluation'
    _description = 'Performance Evaluation'
    _order = 'id desc'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  default=lambda self: self.env.user.employee_id)
    employee_hod_id = fields.Many2one(related='employee_id.parent_id', string='Department Head')
    performance_id = fields.Many2one('performance.evaluation',
                                     string='Parent Revised Performance Evaluation', copy=False)
    performance_ids = fields.One2many('performance.evaluation', 'performance_id',
                                      string='Child Revised Performance Evaluation')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('mid_term', 'Mid Term Evaluation'),
        ('final_eval', 'Final Evaluation'),
        ('revised', 'Revised'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ],
        default='draft',
        tracking=True,
        string='Status',
        copy=False
    )
    goal_template_id = fields.Many2one('goal.template', string='Goal Template',
                                       default=lambda self: self.env.company.goal_template_id)
    goal_line_ids = fields.One2many('performance.goal.line', 'performance_id', string='Goal Lines')
    mid_term_score = fields.Float(string='Avg. Mid Term Score', compute='_compute_goal_score',
                                  store=True)
    final_score = fields.Float(string='Final Score', compute='_compute_goal_score', store=True)
    survey_ids = fields.One2many('survey.survey', 'performance_id', string='Surveys')

    year_id = fields.Many2one('year.year', string='Year')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    mid_year_date = fields.Date(string='Mid Year Date', compute='_compute_mid_year_date',
                                store=True)
    description = fields.Html('Description')
    # mid_term_evaluated = fields.Boolean(string='Mid Term Evaluated')
    mid_term_evaluated = fields.Boolean(
        string='Mid Term Evaluated',
        compute='_compute_mid_term_evaluated',
        store=True
    )
    goal_modified_reason_ids = fields.One2many('goal.modified.reason', 'performance_id',
                                               string='Goal Modified Reasons')
    performance_improvement_ids = fields.One2many('performance.improvement.plan', 'performance_id',
                                                  string='Performance Improvement Plan')
    mid_term_rating = fields.Selection(
        selection=[
            ('on_track', 'On Track'),  # --> 1
            ('off_track', 'Off Track'),  # --> 0
        ],
        string='Mid Term Evaluation',
        copy=False,
    )
    final_rating = fields.Selection(
        selection=[
            ('0', '0%'),
            ('1', '25% - (Unacceptable)'),
            ('2', '50% - (Below Expectations)'),
            ('3', '75% - (Meets Expectations)'),
            ('4', '100% - (Exceeds Expectations)'),
        ],
        default='0',
        string='Avg. Final Rating',
        compute='_compute_goal_score',
        store=True,
    )
    rating_text = fields.Selection(
        selection=[
            ('0', ''),
            ('1', 'Unacceptable #1'),
            ('2', 'Below Expectations #2'),
            ('3', 'Meets Expectations #3'),
            ('4', 'Exceeds Expectations #4'),
        ],
        default='0',
        string='Rating',
        compute='_compute_goal_score',
    )

    @api.constrains('employee_id', 'year_id', 'performance_id')
    def _check_unique_employee_year(self):
        for record in self:
            # Ignore if this is a revised evaluation
            if record.performance_id:
                continue

            # Search for other evaluations with the same employee and year
            existing = self.search([
                ('employee_id', '=', record.employee_id.id),
                ('year_id', '=', record.year_id.id),
                ('id', '!=', record.id),
                ('performance_id', '=', False)  # only consider non-revised plans
            ])
            if existing:
                raise ValidationError(
                    "An evaluation for this employee and year already exists. "
                    "If you want to revise it, please create a revision from the existing record."
                )

    @api.onchange('year_id')
    def _onchange_year_id(self):
        if self.year_id:
            self.date_from = self.year_id.date_from
            self.date_to = self.year_id.date_to
        else:
            self.date_from = False
            self.date_to = False

    @api.depends('goal_line_ids.mid_term_evaluated')
    def _compute_mid_term_evaluated(self):
        for rec in self:
            rec.mid_term_evaluated = bool(rec.goal_line_ids) and all(
                rec.goal_line_ids.mapped('mid_term_evaluated')
            )

    def action_create_performance_improvement(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Performance Improvement Plans"),
            'view_mode': 'form',
            'res_model': 'performance.improvement.plan',
            'views': [(False, 'form')],
            'context': {
                'default_performance_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_start_date': self.date_to + timedelta(days=1),
            },
        }

    def action_open_performance_improvements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Performance Improvement Plans"),
            'view_mode': 'list,form',
            'res_model': 'performance.improvement.plan',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.performance_improvement_ids.ids)],
        }

    def action_create_survey(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Choose Survey"),
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'choose.survey',
            'views': [(False, 'form')],
            'context': {
                'default_performance_id': self.id,
            },
        }

    def action_open_surveys(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Goal Surveys"),
            'view_mode': 'list,form',
            'res_model': 'survey.survey',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.survey_ids.ids)],
        }

    @api.model
    def cron_goal_performance_evaluation(self):
        """Cron to automatically update performance evaluation state based on dates.

        - If today >= mid_year_date and state is 'confirmed', move to 'mid_term'.
        - If today >= date_to and state is 'mid_term' and mid_term_evaluated is True, move to 'final_eval'.
        - Assign a todo activity to the HOD for evaluation confirmation.
        """
        today = date.today()

        # Step 1: Move confirmed records to mid_term if today >= mid_year_date
        confirmed_records = self.search([
            ('state', '=', 'confirmed'),
            ('mid_year_date', '<=', today)
        ])
        for rec in confirmed_records:
            rec.state = 'mid_term'
            if rec.employee_hod_id.user_id:
                rec.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    user_id=rec.employee_hod_id.user_id.id,
                    summary=_("Mid-Term Evaluation"),
                    note=_("Please complete the mid-term evaluation for this performance."),
                    date_deadline=today + timedelta(days=3)
                )

        # Step 2: Move mid_term evaluated records to final_eval if today >= date_to - X days
        mid_term_records = self.search([
            ('state', '=', 'mid_term'),
            ('mid_term_evaluated', '=', True),
        ])
        for rec in mid_term_records:
            trigger_date = rec.date_to - timedelta(
                days=rec.company_id.final_eval_trigger_days_before)
            if today >= trigger_date:
                rec.state = 'final_eval'
                if rec.employee_hod_id.user_id:
                    rec.activity_schedule(
                        activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                        user_id=rec.employee_hod_id.user_id.id,
                        summary=_("Final Evaluation"),
                        note=_("Please complete the final evaluation for this performance."),
                        date_deadline=today + timedelta(days=3)
                    )

    @api.onchange('goal_template_id')
    def _onchange_goal_template_id(self):
        self.goal_line_ids = [Command.clear()]

    def action_generate_lines(self):
        self.goal_line_ids = [
            Command.create({
                'weight': line.weight,
                'description': line.description,
                'evaluation_category_id': line.evaluation_category_id.id,
            }) for line in self.goal_template_id.goal_template_line_ids
        ]

    def action_open_revised_goal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Revised Goal"),
            'view_mode': 'list,form',
            'res_model': 'performance.evaluation',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.performance_ids.ids)],
        }

    def action_open_parent_goal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Parent Goal"),
            'view_mode': 'form',
            'res_model': 'performance.evaluation',
            'views': [(False, 'form')],
            'res_id': self.performance_id.id
        }

    def action_request_revision(self):
        self.ensure_one()

        goal_lines_commands = []

        for rec in self.goal_line_ids:
            employee_lines = []
            for line in rec.employee_goal_line_ids:
                employee_lines.append(Command.create({
                    'sequence': line.sequence,
                    'goal_line_id': line.id,
                    'name': line.name,
                    'deadline': line.deadline,
                    'weight': line.weight,
                    'description': line.description,
                    'evaluation_method_id': line.evaluation_method_id.id,
                }))

            goal_lines_commands.append(Command.create({
                'sequence': rec.sequence,
                'weight': rec.weight,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
                'description': rec.description,
                'evaluation_category_id': rec.evaluation_category_id.id,
                'employee_goal_line_ids': employee_lines,
            }))

        revised = self.env['performance.evaluation'].create({
            'performance_id': self.id,
            'year_id': self.year_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'name': f"REVISED GOAL: {self.name}",
            'employee_id': self.employee_id.id,
            'goal_template_id': self.goal_template_id.id,
            'description': self.description,
            'goal_line_ids': goal_lines_commands,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _("Revised Goal"),
            'res_model': 'performance.evaluation',
            'view_mode': 'form',
            'res_id': revised.id,
            'target': 'current',
        }

    def action_submit(self):
        """Submit the evaluation for department head review.

           This method transitions the evaluation state to 'pending' and
           schedules a review activity for the assigned Department Head (HOD).
           The HOD will receive a To-Do activity with a deadline of 3 days.

           Raises:
               UserError: If no Department Head is assigned to the employee.
               UserError: If the assigned Department Head does not have a related user.
       """
        self.ensure_one()
        if not self.goal_line_ids:
            raise UserError(
                _('No Category Lines are added please generate the lines first and submit for approve.'))
        for rec in self.goal_line_ids:
            if not rec.employee_goal_line_ids:
                raise UserError(
                    _('No Goal Lines are added please add the lines under each category first and submit for approve.'))
            for goal in rec.employee_goal_line_ids:
                if not goal.name:
                    raise UserError(
                        _('Each goal line must have a Goal Name. Please provide it before proceeding.'))
                if not goal.description:
                    raise UserError(
                        _('Each goal line must include a Goal Definition. Please fill it in before proceeding.'))
                if not goal.deadline:
                    raise UserError(
                        _('Each goal line must have a Deadline specified. Please set it before proceeding.'))

        if not self.employee_hod_id:
            raise UserError(_("A Department Head is not assigned for this employee."))

        if not self.employee_hod_id.user_id:
            raise UserError(_("The Department Head does not have an assigned user."))
        self.state = 'pending'
        self.activity_schedule(
            activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
            user_id=self.employee_hod_id.user_id.id,
            summary=_("Performance Goal Evaluation Review"),
            note=_("Please review and confirm the submitted Goal evaluation."),
            date_deadline=fields.Date.today() + timedelta(days=3)
        )

    def _mark_activity_done(self, activity_type_xml_id=False):
        """Mark pending activities of a specific type as done."""
        self.ensure_one()
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('user_id', '=', self.env.user.id),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    def _validate_hod(self):
        """Validate that the current user is the assigned Department Head.

            Ensures that only the Department Head linked to the employee can
            perform approval actions on the evaluation form.

            Raises:
                UserError: If the current user is not the assigned Department Head.
        """
        self.ensure_one()
        if self.env.user != self.employee_hod_id.user_id:
            raise UserError(
                _("Only the Head of Department assigned to this employee can confirm this request."))

    def _perform_action(self, state):
        self.ensure_one()
        self._validate_hod()
        self.state = state
        self._mark_activity_done()

    def action_confirm(self):
        """Confirm the performance evaluation.

           This method validates that the user has the required HOD permissions
           before marking the evaluation as `confirmed`. It also completes the
           related To-Do activity scheduled for the user.

           Raises:
               UserError: If the user is not the assigned Department Head.
       """
        self._perform_action('confirmed')
        if self.performance_id:
            self.performance_id._perform_action('revised')

    def action_cancel(self):
        """Confirm the performance evaluation.

           This method validates that the user has the required HOD permissions
           before marking the evaluation as `confirmed`. It also completes the
           related To-Do activity scheduled for the user.

           Raises:
               UserError: If the user is not the assigned Department Head.
       """
        self.ensure_one()
        self._validate_hod()
        return self._call_reason_wizard('cancel')

    def action_reset_to_draft(self):
        """Reset the performance evaluation."""
        self._perform_action('draft')

    def action_rfc(self):
        self.ensure_one()
        self._validate_hod()
        return self._call_reason_wizard('draft')

    def _call_reason_wizard(self, action_type):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reason'),
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'goal.modified.reason',
            'views': [(False, 'form')],
            'context': {
                'default_performance_id': self.id,
                'default_action_type': action_type,
            }
        }

    def action_user_cancel(self):
        """Confirm the performance evaluation.

           This method validates that the user has the required HOD permissions
           before marking the evaluation as `confirmed`. It also completes the
           related To-Do activity scheduled for the user.

           Raises:
               UserError: If the user is not the assigned Department Head.
       """
        self.ensure_one()
        self.state = 'cancel'


    def action_mid_term_done(self):
        """Mark the mid-term evaluation as completed (user action)."""
        for rec in self:
            if not all(line.mid_term_evaluated for line in rec.goal_line_ids):
                raise UserError(
                    "All goal lines must be evaluated before completing the mid-term evaluation."
                )

            if not rec.mid_term_rating:
                raise UserError(
                    "Please provide a mid-term rating before completing the evaluation."
                )

            self.mid_term_evaluated = True
            self._mark_activity_done()


    def action_final_term_done(self):
        """Mark the final-term evaluation as completed.
        """
        if all(rec.final_eval_done for rec in self.goal_line_ids):
            self._perform_action('done')

    @api.depends('goal_line_ids', 'goal_line_ids.mid_term_score', 'goal_line_ids.final_score')
    def _compute_goal_score(self):
        for rec in self:
            mid_term_score = rec.goal_line_ids.mapped('mid_term_score')
            if mid_term_score:
                rec.mid_term_score = sum(mid_term_score) / len(mid_term_score)
            else:
                rec.mid_term_score = 0
            final_score = sum(rec.goal_line_ids.mapped('final_score'))
            rec.final_score = final_score
            if final_score <= 0:
                bucket = 0
            elif final_score <= 25:
                bucket = 25
            elif final_score <= 50:
                bucket = 50
            elif final_score <= 75:
                bucket = 75
            else:
                bucket = 100

            rating_map = {
                0: '0',
                25: '1',
                50: '2',
                75: '3',
                100: '4',
            }

            final_rating = rating_map[bucket]
            rec.final_rating = final_rating
            rec.rating_text = final_rating

    @api.depends('date_from', 'date_to')
    def _compute_mid_year_date(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.mid_year_date = rec.date_from + relativedelta(months=+6)

    @api.model
    def fetch_dashboard_data(self, company_id, year_id):
        """
        Fetch Performance Dashboard data filtered by company
        """
        Evaluation = self.env['performance.evaluation']

        domain = [
            ('year_id', '=', year_id),
            ('company_id', '=', company_id),
            ('state', 'in', ['mid_term', 'final_eval', 'done']),
        ]

        records = Evaluation.search(domain)

        total_records = len(records)

        # -------------------------
        # 1. Mid-Year Status
        # -------------------------
        mid_year_records = records.filtered(lambda r: r.mid_term_evaluated)

        mid_year_evaluated = len(mid_year_records)

        no_track = mid_year_records.filtered(lambda r: r.mid_term_rating == '')
        on_track = mid_year_records.filtered(lambda r: r.mid_term_rating == 'on_track')
        off_track = mid_year_records.filtered(lambda r: r.mid_term_rating == 'off_track')

        no_track_pct = (len(no_track) / mid_year_evaluated * 100) if mid_year_evaluated else 0
        on_track_pct = (len(on_track) / mid_year_evaluated * 100) if mid_year_evaluated else 0
        off_track_pct = (len(off_track) / mid_year_evaluated * 100) if mid_year_evaluated else 0

        # -------------------------
        # 2. Year-End Evaluation
        # -------------------------
        final_records = records.filtered(lambda r: r.final_rating and r.final_rating != '0')

        year_end_evaluated = len(final_records)

        avg_annual_rating = (
            sum(float(r.final_rating) for r in final_records) / year_end_evaluated
            if year_end_evaluated else 0
        )

        # -------------------------
        # 3. Annual Performance Distribution
        # -------------------------
        rating_distribution = {
            '1': 0,
            '2': 0,
            '3': 0,
            '4': 0,
        }

        for rec in final_records:
            if rec.final_rating in rating_distribution:
                rating_distribution[rec.final_rating] += 1

        # -------------------------
        # 4. YoY Improvement Analysis
        # -------------------------
        improved = stable = declined = 0
        prev_year_name = ""
        current_year = self.env['year.year'].browse(year_id)

        prev_year = self.env['year.year'].search([
            ('sequence', '<', current_year.sequence)
        ], limit=1, order='sequence desc')
        avg_prev_annual_rating = 0
        if prev_year:
            prev_year_name = prev_year.name
            prev_year_records = Evaluation.search([
                ('year_id', '=', prev_year.id),
                ('company_id', '=', company_id),
                ('final_rating', '!=', '0'),
                ('state', 'in', ['done']),
            ])

            if prev_year_records:
                avg_prev_annual_rating = (
                        sum(float(r.final_rating) for r in prev_year_records)
                        / len(prev_year_records)
                )

        for rec in final_records:
            if not rec.year_id or prev_year:
                continue
            # prev_year = self.env['year.year'].search([
            #     ('sequence', '<', rec.year_id.sequence)
            # ], limit=1, order='sequence desc')

            prev_eval = Evaluation.search([
                ('employee_id', '=', rec.employee_id.id),
                ('year_id', '=', prev_year.id),
                ('company_id', '=', company_id),
                ('final_rating', '!=', '0'),
                ('state', 'in', ['done']),
            ], limit=1)

            if not prev_eval:
                continue

            if float(rec.final_score) > float(prev_eval.final_score):
                improved += 1
            elif float(rec.final_score) == float(prev_eval.final_score):
                stable += 1
            else:
                declined += 1

            # avg_prev_annual_rating = (
            #         sum(float(r.final_rating) for r in prev_eval)
            #         / len(prev_eval)
            # )

        yoy_total = improved + stable + declined
        yoy_improvement_rate = (improved / yoy_total * 100) if yoy_total else 0

        # -------------------------
        # Final Dashboard Payload
        # -------------------------
        return {
            'performance_overview': {
                'prev_year_name': prev_year_name,
                'current_year_name': current_year.name,
                'mid_year_evaluated': mid_year_evaluated,
                'total_records': total_records,
                'no_track_pct': round(no_track_pct, 2),
                'on_track_pct': round(on_track_pct, 2),
                'off_track_pct': round(off_track_pct, 2),
                'year_end_evaluated': year_end_evaluated,
                'avg_annual_rating': round(avg_annual_rating, 2),
                'avg_prev_annual_rating': round(avg_prev_annual_rating, 2),
                'yoy_improvement_rate': round(yoy_improvement_rate, 2),
            },
            'annual_distribution': {
                'rating_4': rating_distribution['4'],
                'rating_3': rating_distribution['3'],
                'rating_2': rating_distribution['2'],
                'rating_1': rating_distribution['1'],
            },
            'yoy_analysis': {
                'improved': improved,
                'stable': stable,
                'declined': declined,
            }
        }

    @api.model
    def load_dashboard_filter(self, company_id):
        return {
            "year_ids": self.env['year.year'].search_read(
                [('company_id', '=', company_id)],
                ['name']
            )
        }

