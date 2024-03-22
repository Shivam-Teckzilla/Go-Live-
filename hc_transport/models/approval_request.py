from odoo import api, fields, models,SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    res_model = fields.Char("Res Model")
    res_id = fields.Integer("Res ID")
    transport_rates_id = fields.Many2one('transport.rates', string='Transport Rates')
    action_ids = fields.Many2one("res.partner", string='Registration ID')
    sale_tbs_id = fields.Many2one("tbs.sale", string="TBS Sale")
    quality_approval = fields.Many2one("quality.check", string="Quality Approval")

    def action_approve(self, approver=None):
        self._ensure_can_approve()

        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved'})
        self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

        # For approving Approval Request
        if self.res_model:
            res = self.env[self.res_model].search([('id', '=', self.res_id)])
            res.action_approve()

        # quality_approval = self.quality_approval
        # quality_approval.action_approve()

        transport_rates = self.transport_rates_id
        transport_rates.action_approve()

        sale_tbs_ids = self.sale_tbs_id
        sale_tbs_ids.action_approve()

        action_idssss = self.action_ids
        action_idssss.action_approve()

    def view_related_doc(self):
        res_model = None
        res_id = None

        if self.res_id:
            res_model = self.res_model
            res_id = self.res_id

        if self.transport_rates_id:
            res_model = 'transport.rates'
            res_id = self.transport_rates_id.id
        elif self.action_ids:
            res_model = 'res.partner'
            res_id = self.action_ids.id
        elif self.sale_tbs_id:
            res_model = 'tbs.sale'
            res_id = self.sale_tbs_id.id

        if res_model and res_id:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': res_model,
                'domain': [('id', '=', res_id)],
                'target': 'current',
            }


class ResPartner(models.Model):
    _inherit = "res.partner"


class HrEmployee(models.Model):
    _inherit = "hr.employee"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    location_rate_id = fields.Many2one("transporter.location", string="Depot")
    total_freight_rate = fields.Float("Total Freight Rate")
    tab_sale = fields.Char(string="TBS Sale")
    purchase_total_freight_rate = fields.Float("Total Freight Rate")
    tab_purchase = fields.Char(string="TBS Purchase")
    transporter = fields.Boolean("Transporter Type", default=False)

    @api.onchange('order_line.product_id')
    def onchange_product_id(self):
        for order in self:
            if order.order_line:
                product = order.order_line[0].product_id
                order.transporter = product.transporter

    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        # if not all(order._can_be_confirmed() for order in self):
        # 	raise UserError(_(
        # 		"The following orders are not in a state requiring confirmation: %s",
        # 		", ".join(self.mapped('display_name')),
        # 	))

        self.order_line._validate_analytic_distribution()

        for order in self:
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_lock()

        po = self._get_purchase_orders()
        if po:
            self.po_ref = po[0].name

        # po_id = self.env['purchase.order'].search([('origin','=', self.name)])
        # if po_id:
        #     self.po_ref = po_id.name

        return True


class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Inherited this code to only run from sales token and create a delivery
    # def _action_launch_stock_rule(self, previous_product_uom_qty=False):
    #     """
    #     Launch procurement group run method with required/custom fields generated by a
    #     sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
    #     depending on the sale order line product rule.
    #     """
    #     if self._context.get('create_delivery', False):
    #         if self._context.get("skip_procurement"):
    #             return True
    #         precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #         procurements = []
    #         for line in self:
    #             line = line.with_company(line.company_id)
    #             if line.state != 'sale' or line.order_id.locked or not line.product_id.type in ('consu', 'product'):
    #                 continue
    #             qty = line._get_qty_procurement(previous_product_uom_qty)
    #             if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
    #                 continue
    #
    #             group_id = line._get_procurement_group()
    #             if not group_id:
    #                 group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
    #                 line.order_id.procurement_group_id = group_id
    #             else:
    #                 # In case the procurement group is already created and the order was
    #                 # cancelled, we need to update certain values of the group.
    #                 updated_vals = {}
    #                 if group_id.partner_id != line.order_id.partner_shipping_id:
    #                     updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
    #                 if group_id.move_type != line.order_id.picking_policy:
    #                     updated_vals.update({'move_type': line.order_id.picking_policy})
    #                 if updated_vals:
    #                     group_id.write(updated_vals)
    #
    #             values = line._prepare_procurement_values(group_id=group_id)
    #             product_qty = line.product_uom_qty - qty
    #
    #             line_uom = line.product_uom
    #             quant_uom = line.product_id.uom_id
    #             product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
    #             procurements.append(line._create_procurement(product_qty, procurement_uom, values))
    #         if procurements:
    #             self.env['procurement.group'].run(procurements)
    #
    #         # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
    #         orders = self.mapped('order_id')
    #         for order in orders:
    #             pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
    #             if pickings_to_confirm:
    #                 # Trigger the Scheduler for Pickings
    #                 pickings_to_confirm.action_confirm()
    #         return True


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def view_related_doc(self):
        res_model = None
        res_id = None

        if self.transport_rates_id:
            res_model = 'transport.rates'
            res_id = self.transport_rates_id.id
        elif self.action_ids:
            res_model = 'res.partner'
            res_id = self.action_ids.id
        elif self.sale_tbs_id:
            res_model = 'tbs.sale'
            res_id = self.sale_tbs_id.id

        if res_model and res_id:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': res_model,
                'res_id': res_id,
                'target': 'current',
            }

    def button_approve(self, force=False):
        result = super(PurchaseOrder, self).button_approve(force=force)
        self.with_context(no_picking=False)._create_picking()
        return result


