
from odoo import fields, models


class LinkedinComments(models.Model):
    """class for retrieving comments of shared post"""
    _name = 'linkedin.comments'

    post_id = fields.Integer(string="Post ID",
                             help="Post id of the particular post")
    comments_id = fields.Char(string="Comments ID",
                              help="For specifing the comments id")
    linkedin_comments = fields.Char(string="Comments",
                                    help="To add the posts comments")
