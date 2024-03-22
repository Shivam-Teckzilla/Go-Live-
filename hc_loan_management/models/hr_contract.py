# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



class ContractInherit(models.Model):
    _inherit = 'hr.contract'

    loan_req = fields.Boolean("Loan Request")
    interest_type = fields.Selection([
        ('with_interest', 'With Interest'),
        ('without_interest', 'Without Interest'),
        
    ], string="Interest Type", copy=False, )
    interest_amount = fields.Float("Interest(%)")


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    contract_id = fields.Many2one('hr.contract', string="Contract")
    loan_req = fields.Boolean(
        'Loan Request',
        related='contract_id.loan_req',
        store=True
    )
    interest_type = fields.Selection([
        ('with_interest', 'With Interest'),
        ('without_interest', 'Without Interest'),
        
    ],related='contract_id.interest_type', string="Interest Type", copy=False, )
    
    interst = fields.Selection([
        ('with_interest', 'With Interest'),
        ('without_interest', 'Without Interest'),
        
    ],related='contract_id.interest_type', string="Interest Type", copy=False, )
    interest_amount = fields.Float("Interest(%)", related='contract_id.interest_amount',)

    interst_amount = fields.Float("Interest(%)", related='contract_id.interest_amount',)
