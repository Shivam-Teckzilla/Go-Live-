# -*- coding: utf-8 -*-
from odoo import api, fields, models ,_
from num2words import num2words


class ProductTemplate(models.Model):
	_inherit = 'product.template'

	based_on = fields.Selection([
		('conf_po', 'PO'),
		('conf_so', 'SO')], string='Based On')
	partner_id = fields.Many2one('res.partner', string='Partner')
	transporter = fields.Boolean("Transporter applicable", related = 'categ_id.transporter')
	make = fields.Char("Make")

	
class ProductCatagory(models.Model):
	_inherit = "product.category"

	transporter = fields.Boolean("Transporter applicable",default = False)

