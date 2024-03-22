from odoo import api, fields, models, _
	
class ProductCatagory(models.Model):
	_inherit = "product.category"

	tbs = fields.Boolean("Sent", default = False)
	transporter = fields.Boolean("Transporter applicable", default=False)
	product_uom = fields.Many2one('uom.uom')
	seq_id = fields.Many2one('ir.sequence')
	tbs_applied = fields.Boolean("TBS Applied", default = False)

