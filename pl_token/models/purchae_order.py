from odoo import api, fields, models, SUPERUSER_ID,_
from num2words import num2words


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    debit_notes_ids = fields.Many2many("account.move", 'po_debit_rel', string="Debit Note",
                                       domain="[('move_type', '=', 'in_refund')]")
    token_id = fields.Many2one("purchase.token", string="Inward token")
    p_and_f = fields.Char('P & F')

    def action_debit_notes(self):
        return {
            'name': _('Debit Note'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.debit_notes_ids.ids)],

        }

    def _create_picking(self):
        if self._context.get('no_picking'):
            StockPicking = self.env['stock.picking']
            for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
                if any(product.type in ['product', 'consu'] for product in order.order_line.product_id):
                    order = order.with_company(order.company_id)
                    pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                    if not order.token_id:
                        if not pickings:
                            res = order._prepare_picking()
                            picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                            pickings = picking
                        else:
                            picking = pickings[0]
                    else:
                        res = order._prepare_picking()
                        picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                        pickings = picking
                    moves = order.order_line._create_stock_moves(picking)
                    moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                    seq = 0
                    for move in sorted(moves, key=lambda move: move.date):
                        seq += 5
                        move.sequence = seq
                    moves._action_assign()
                    # Get following pickings (created by push rules) to confirm them as well.
                    forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
                    (pickings | forward_pickings).action_confirm()
                    picking.message_post_with_source(
                        'mail.message_origin_link',
                        render_values={'self': picking, 'origin': order},
                        subtype_xmlid='mail.mt_note',
                    )
            return True


class InheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    po_token_bool = fields.Boolean(default=False)
    make = fields.Char("Make", related="product_id.make")
    categ_id = fields.Many2one('product.category', string="Category", related="product_id.categ_id")