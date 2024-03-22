from odoo import api, fields, models, _


class TokenType(models.Model):
	_name = 'token.type'
	_description = 'Token Type'
	_rec_name = 'name'

	name = fields.Char(compute='compute_rec_name')
	token_type = fields.Char(string='Token Type')
	code = fields.Char('Code', required = True)
	for_token_type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string='For')
	sequence_button_hide = fields.Boolean("sequence Button Hide", default = False)
	product_category = fields.Many2one('product.category', string="Product Category")
	sequence_id = fields.Many2one('ir.sequence',"Related Sequence")

	def compute_rec_name(self):
		for rec in self:
			rec.name = str(rec.token_type) + " / " + str(rec.product_category.name)

	def open_related_seq(self):
		return {
				'name': ('Related Sequence'),
				'type': 'ir.actions.act_window',
				'res_model': 'ir.sequence',
				'view_mode': 'form',
				'domain': [('id','=',self.sequence_id.id)],
				}

	def generate_sequence(self):
		if self.for_token_type == 'sale':
			sequence_model = self.env['ir.sequence'].sudo().create({
				'name': self.token_type,
				'code': f"sale.token.{self.code}",
				'prefix' : f"{self.code}/", 
				'padding' : 4 ,
			})
			self.write({'sequence_button_hide': True,'sequence_id':sequence_model.id})
		elif self.for_token_type == 'purchase':
			sequence_model = self.env['ir.sequence'].sudo().create({
				'name': self.token_type,
				'code': f"purchase.token.{self.code}",
				'prefix' : f"{self.code}/", 
				'padding' : 4 ,
			})
			self.write({'sequence_button_hide': True,'sequence_id':sequence_model.id})



class TrailerType(models.Model):
	_name = 'trailer.type'
	_description = 'Trailer Type'
	_rec_name = 'name'

	name = fields.Char(string='Name')


class RejectName(models.Model):
	_name = 'reject.name'
	_description = 'Reject Name'
	_rec_name = 'reject_reason'

	name = fields.Char(string='Name')
	reject_reason = fields.Char(string='Reject Reason')


class CustomeOnHold(models.Model):
	_name = 'reason.reason'
	_description = 'Token Reason'
	_rec_name = 'on_hold'

	on_hold = fields.Char(string='Name')
	token_status = fields.Selection([
		('onhold', 'On Hold'),
		('released', 'Released')], string='Token Reason', default='onhold')


