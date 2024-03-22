# -*- coding: utf-8 -*-
from odoo import api, fields, models ,_
from num2words import num2words

class SaleOrder(models.Model):
	_inherit = 'sale.order'


	po_ref = fields.Char(string='Po Ref')
	trasfer_status = fields.Selection([
		('harp_chemical', ' By Harp Chemical'),
		('customer', 'By Customer'),
	], string='Transporter Type',)
	transporter = fields.Boolean("Transporter applicable", related='order_line.product_id.transporter' )

	amount_word = fields.Char(string ="Amount in Word", compute="_compute_amount_word")
	transfer_name = fields.Many2one("res.partner", string = "Transporter Name",
								readonly= False, )

	
	
	def _compute_amount_word(self):
		for order in self:
			amount_in_words = num2words(order.amount_total, to='currency', lang='en')
			order.amount_word = amount_in_words

