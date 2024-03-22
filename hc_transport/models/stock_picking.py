from odoo import api, fields, models, exceptions
from odoo.exceptions import ValidationError
from datetime import timedelta

	
class StockPicking(models.Model):
	_inherit = "stock.picking"

	demurrage_day = fields.Float("Demurrage Days")
	sale_id = fields.Many2one("sale.order", string = "Sale Order")
	location_rate_id = fields.Many2one("transporter.location", string= "Depot", related = "sale_id.location_rate_id")
	tot_req_quant = fields.Float(compute='compute_total_req_quant',store=True)
	received_qty = fields.Float(compute='compute_rec_quant',store=True)

	@api.depends('purchase_id','purchase_id.order_line','purchase_id.order_line.product_qty')
	def compute_total_req_quant(self):
		for rec in self:
			if rec.purchase_id:
				rec.tot_req_quant = rec.purchase_id.order_line[0].product_qty

	@api.depends('purchase_id', 'purchase_id.order_line', 'purchase_id.order_line.qty_received')
	def compute_rec_quant(self):
		for rec in self:
			if rec.purchase_id:
				rec.received_qty = rec.purchase_id.order_line[0].qty_received

	def action_view_po(self):
		po = self.env['purchase.order'].search([('name','=',self.origin)])
		return {
			'name': 'Purchase Order',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'purchase.order',
			'domain': [('id', '=',po.id)],
			'context': {
				'create': False,
			},
		}
		