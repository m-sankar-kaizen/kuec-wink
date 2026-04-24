# -*- coding: utf-8 -*-
from odoo import fields, models, _, Command


class ChooseSurvey(models.TransientModel):
    _name = 'choose.survey'
    _description = 'Choose Survey'

    performance_id = fields.Many2one('performance.evaluation', string='Performance Evaluation')
    survey_id = fields.Many2one('survey.survey', string='Survey')

    def action_create_survey(self):
        self.ensure_one()
        context = {
            'default_performance_id': self.performance_id.id,
            'default_survey_type': 'appraisal',
        }
        if self.survey_id:
            updated_context = self._get_survey_context()
            context.update(updated_context)
        return {
            'type': 'ir.actions.act_window',
            'name': _("Goal Survey"),
            'view_mode': 'form',
            'res_model': 'survey.survey',
            'views': [(False, 'form')],
            'context': context,
        }

    def _get_survey_context(self):
        survey = self.survey_id
        questions = survey.question_and_page_ids.copy_data()
        return {
            'default_description': survey.description,
            'default_description_done': survey.description_done,
            'default_questions_layout': survey.questions_layout,
            'default_progression_mode': survey.progression_mode,
            'default_questions_selection': survey.questions_selection,
            'default_users_can_go_back': survey.users_can_go_back,
            'default_access_mode': survey.access_mode,
            'default_users_login_required': survey.users_login_required,
            'default_is_attempts_limited': survey.is_attempts_limited,
            'default_is_time_limited': survey.is_time_limited,
            'default_time_limit': survey.time_limit,
            'default_scoring_type': survey.scoring_type,
            'default_scoring_success_min': survey.scoring_success_min,
            'default_certification': survey.certification,
            'default_certification_report_layout': survey.certification_report_layout,
            'default_certification_mail_template_id': survey.certification_mail_template_id,
            'default_certification_give_badge': survey.certification_give_badge,
            'default_certification_badge_id': survey.certification_badge_id,
            'default_session_speed_rating': survey.session_speed_rating,
            'default_session_speed_rating_time_limit': survey.session_speed_rating_time_limit,
            'default_question_and_page_ids': [Command.create(question) for question in questions],
        }
