# -*- coding: utf-8 -*-
from odoo import api, models, fields


class RejectReason(models.TransientModel):
    _name = 'on.hold'
    _description = 'ON Hold'

    on_hold_id = fields.Many2one('reason.reason', string='On Hold', required=True, domain="[('token_status', '=', 'onhold')]")
    record_id = fields.Many2one('purchase.token')

    def on_hold_button(self):
        refuse_id = self.env['purchase.token'].browse(self._context.get('active_id'))
        refuse_id.write({'on_hold_id': self.on_hold_id})
        refuse_id.write({'on_hold_button': True})
        refuse_id.write({'show_ribbon': not refuse_id.show_ribbon})
        return {'type': 'ir.actions.act_window_close'}
    

class ResumeReason(models.TransientModel):
    _name = 'resume.reason'
    _description = 'Resume Reason'

    resume_reason_id = fields.Many2one('reason.reason', string='Resume', required=True, domain="[('token_status', '=', 'released')]")
    record_id = fields.Many2one('purchase.token')

   
    def resume_reason_button(self):
        refuse_id = self.env['purchase.token'].browse(self._context.get('active_id'))

        if self.resume_reason_id:
            refuse_id.write({
                'resume_reason_id': self.resume_reason_id,
                'show_ribbon': not refuse_id.show_ribbon,
                'resume_reason_button': True ,
            })

        return {'type': 'ir.actions.act_window_close'}