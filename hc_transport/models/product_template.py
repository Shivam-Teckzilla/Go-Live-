from odoo import api, fields, models, _


class InheritProductTemplate(models.Model):
    _inherit = "product.template"

    _is_freight = fields.Boolean(default=False)
    product_code = fields.Char('Product Code')

    @api.model
    def create(self,vals):
        res = super().create(vals)
        if res.categ_id.seq_id:
            res.product_code = res.categ_id.seq_id._next()
        return res
