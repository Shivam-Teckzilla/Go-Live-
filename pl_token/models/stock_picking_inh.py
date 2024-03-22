from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form


# Wizard class for error
class ErrorWizard(models.TransientModel):
    _name = "confirm.lock.po.wizard"

    message = fields.Char()
    def action_confirm_lock(self):
        active_id = self.env['stock.picking'].browse(self._context.get('active_id'))
        po_search = self.env['purchase.order'].search([('name', '=', active_id.origin)])

        if po_search:
            po_search.button_done()
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    party_bill_number = fields.Char("Party Bill Number", requried=True)
    token_id = fields.Many2one("purchase.token", String="Token ID")
    fetch_data_button = fields.Boolean("Sent", default=False)

    def action_fetch_date(self):
        for picking in self:
            party_bill_number = picking.party_bill_number
            origin = picking.origin

            purchase_token = self.env['purchase.token'].search([
                ('party_bill_no', '=', party_bill_number),
            ], limit=1)

            if purchase_token:
                picking.token_id = purchase_token.id
                picking.fetch_data_button = True
                self.token_id.write({'name_id': picking.purchase_id.id})


            else:
                raise ValidationError("Token Data Not Found !!!")

        return True

    def _pre_action_done_hook(self):
        for picking in self:
            if all(not move.picked for move in picking.move_ids):
                picking.move_ids.picked = True
        if not self.token_id:
            if not self.env.context.get('skip_backorder'):
                pickings_to_backorder = self._check_backorder()
                if pickings_to_backorder:
                    return pickings_to_backorder._action_generate_backorder_wizard(
                        show_transfers=self._should_show_transfers())
        return True

    def button_validate(self):
        ########Customisation###########################

        # Added validation to check qty
        po_search = self.env['purchase.order'].search([('name', '=', self.origin)])
        if self.picking_type_code == 'incoming' and po_search.state != 'done':

            if sum(po_search.order_line.mapped('qty_received')) >= sum(self.move_ids_without_package.mapped('quantity')):
                return {
                    'name': _('Confirm Lock PO'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.lock.po.wizard',
                    'view_mode': 'form',
                    'view_id': self.env.ref('pl_token.confirm_lock_po_wizard_form_view').id,
                    'target': 'new',
                }

        quality_check = self.env['quality.check'].search([('picking_id', '=', self.id)]).filtered(
            lambda x: x.quality_state == 'none')
        if len(quality_check) >= 1:
            raise ValidationError('You need to perform the quality first')
        ########Customisation###########################

        if not self.env.context.get('skip_sanity_check', False):
            self._sanity_check()
        self.message_subscribe([self.env.user.partner_id.id])

        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.picking_type_id.create_backorder != 'always'
            )

        if not self.token_id:
            pickings_to_backorder = self - pickings_not_to_backorder
            pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
            pickings_to_backorder.with_context(cancel_backorder=False)._action_done()

        self.with_context(cancel_backorder=True)._action_done()
        report_actions = self._get_autoprint_report_actions()
        another_action = False
        if self.user_has_groups('stock.group_reception_report'):
            pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
            lines = pickings_show_report.move_ids.filtered(
                lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search(
                    [('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids),
                     ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                    ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                    ('product_qty', '>', 0),
                    ('location_id', 'in', wh_location_ids),
                    ('move_orig_ids', '=', False),
                    ('picking_id', 'not in', pickings_show_report.ids),
                    ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = pickings_show_report.action_view_reception_report()
                    action['context'] = {'default_picking_ids': pickings_show_report.ids}
                    if not report_actions:
                        return action
                    another_action = action

        #### Commented Demmurage Days Wizard ################
        # if self.picking_type_code == "outgoing":
        #     return {
        #         'name': 'Demurrage Days',
        #         'view_mode': 'form',
        #         'view_id': self.env.ref('hc_transport.customer_details_wizard_form').id,
        #         'res_model': 'customer.details.wizard',
        #         'type': 'ir.actions.act_window',
        #         'target': 'new',
        #         'context': {
        #             'default_applicant_id': self.id,
        #         },
        #     }
        if report_actions:
            return {
                'type': 'ir.actions.client',
                'tag': 'do_multi_print',
                'params': {
                    'reports': report_actions,
                    'anotherAction': another_action,
                }
            }

        # if self.party_bill_number and self.partner_id:
        #     token = self.env['purchase.token'].search([
        #         ('party_bill_no', '=', self.party_bill_number),
        #         ('partner_id', '=', self.partner_id.id),
        #         ('product_id', '=', self.move_ids_without_package.product_id.id)
        #     ], limit=1)
        #
        #     if not token:
        #         raise ValidationError('Token not found for party bill number {} and partner {}'.format(
        #             self.party_bill_number, self.partner_id.name))
        #
        #     self.write({
        #         'token_id': token.id,
        #     })
        #
        #     token.write({
        #         'order': self.origin
        #     })
        #
        #     product_id = token.product_id.id
        #     quantity = token.party_bill_quantity
        #
        #     self.move_ids_without_package.write({
        #         'product_id': product_id,
        #         'product_uom_qty': int(quantity),
        #         'quantity': token.net_weight
        #     })