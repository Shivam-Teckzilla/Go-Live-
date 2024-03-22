from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

	
class SaleOrder(models.Model):
	_inherit = "sale.order"

	location_rate_id = fields.Many2one("transporter.location", string= "Depot")
	total_freight_rate = fields.Float("Total Freight Rate")
	tab_sale = fields.Char(string = "TBS Sale")
	purchase_total_freight_rate = fields.Float("Total Freight Rate")
	tab_purchase = fields.Char(string = "TBS Purchase")
	transporter = fields.Boolean("Transporter Type", default = False, copy=False )

	@api.onchange('order_line.product_id')
	def onchange_product_id(self):
		for order in self:
			if order.order_line:
				product = order.order_line[0].product_id
				order.transporter = product.transporter
