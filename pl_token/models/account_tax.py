from odoo import api, fields, models ,_
from num2words import num2words


class AccountTax(models.Model):
	_inherit = 'account.tax'
	
	is_tds = fields.Boolean("Is TDS")


class ResPartner(models.Model):
	_inherit = 'res.partner'

	tds_ids = fields.Many2many("account.tax", string="TDS", domain="[('is_tds', '=', True)]")


