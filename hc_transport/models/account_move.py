from odoo import api, fields, models, exceptions, Command
from odoo.exceptions import ValidationError
from datetime import timedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    tbs_sale_id = fields.Many2one(
        'tbs.sale',
        string='TBS Sale',
        store=True, readonly=False,
    )
    total_freight_rate = fields.Float("Total Freight Rate")
    tab_sale = fields.Char(string="TBS Sale")
    purchase_total_freight_rate = fields.Float("Total Freight Rate")
    tab_purchase = fields.Char(string="TBS Purchase")
    purchase_freight_rate = fields.Float("Rate")

