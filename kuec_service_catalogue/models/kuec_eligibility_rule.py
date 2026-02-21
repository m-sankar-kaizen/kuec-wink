# -*- coding: utf-8 -*-

from odoo import models, fields, api

class KuecEligibilityRule(models.Model):
    _name = 'kuec.eligibility.rule'
    _description = 'KUEC Eligibility Rule'
    _order = 'name'

    name = fields.Char(string='Rule Name', required=True, translate=True)
    code = fields.Char(
        string='Code', 
        required=True, 
        help='Technical code used in Python logic (e.g. ku, kuec, uae).'
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    includes_ids = fields.Many2many(
        'kuec.eligibility.rule', 
        'kuec_eligibility_rule_includes_rel', 
        'rule_id', 
        'includes_id', 
        string='Includes'
    )

    @api.model
    def get_accessible_codes(self, partner):
        """
        Given a res.partner, return a flat set of all eligibility 
        codes accessible to them, including inherited ones via 
        includes_ids. Resolves hierarchy recursively.
        Cycle-safe: tracks visited rule IDs to prevent infinite loops.
        """
        if not partner:
            return {'all'}
        
        tag_ids = partner.eligibility_tag_ids
        if not tag_ids:
            return {'all'}
        
        accessible = set()
        visited = set()
        
        def resolve(rules):
            for rule in rules:
                if rule.id in visited:
                    continue
                visited.add(rule.id)
                accessible.add(rule.code)
                if rule.includes_ids:
                    resolve(rule.includes_ids)
        
        resolve(tag_ids)
        
        # Always include 'all' — visible to everyone
        accessible.add('all')
        return accessible
