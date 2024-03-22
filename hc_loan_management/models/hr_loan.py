# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

class HrLoan(models.Model):
	_name = 'hr.loan'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Loan Request"

	@api.model
	def default_get(self, field_list):
		result = super(HrLoan, self).default_get(field_list)
		if result.get('user_id'):
			ts_user_id = result['user_id']
		else:
			ts_user_id = self.env.context.get('user_id', self.env.user.id)
		result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
		return result

	def _compute_loan_amount(self):
		for loan in self:
			total_paid = 0.0
			total_amount = 0.0
			for line in loan.loan_lines:
				if line.paid:
					total_paid += line.amount
				total_amount += line.amount 
	
			balance_amount = total_amount - total_paid
			loan.total_amount = total_amount
			loan.balance_amount = balance_amount
			loan.total_paid_amount = total_paid

	name = fields.Char(string="Loan Name", default="/", readonly=True, help="Name of the loan")
	date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
	employee_id = fields.Many2one('hr.employee', string="Employee",domain="[('loan_req', '=', True)]", required=True, help="Employee")
	department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
									string="Department", help="Employee")
	installment = fields.Integer(string="No Of Installments", default=1, help="Number of installments")
	payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today(), help="Date of "
																											 "the "
																											 "paymemt")
	loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
	company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
								 default=lambda self: self.env.user.company_id,
								 states={'draft': [('readonly', False)]})
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency",
								  default=lambda self: self.env.user.company_id.currency_id)
	job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position",
								   help="Job position")
	loan_amount = fields.Float(string="Loan Amount", required=True, help="Loan amount")
	total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_compute_loan_amount',
								help="Total loan amount")
	balance_amount = fields.Float(string="Balance Amount", store=True, compute='_compute_loan_amount', help="Balance amount")
	total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute='_compute_loan_amount',
									 help="Total paid amount")

	state = fields.Selection([
		('draft', 'Draft'),
		('approve', 'Approved'),
		('refuse', 'Refused'),
		('cancel', 'Canceled'),
	], string="State", default='draft', track_visibility='onchange', copy=False, )
	approval_request = fields.Many2one('approval.request', string='Approval Request')

	interest_type = fields.Selection([
		('with_interest', 'With Interest'),
		('without_interest', 'Without Interest'),
		
	],related='employee_id.interest_type', string="Interest Type", copy=False, )
	interest_amount = fields.Float("Interest(%)", related='employee_id.interest_amount',)
	approve_button_hide = fields.Boolean(string="approve", default = False)

	

	@api.depends('loan_req')
	def _compute_employee_domain(self):
		for record in self:
			if record.loan_req:
				record.employee_domain = [(6, 0, self.env['hr.employee'].search([('contract_ids.loan_req', '=', True)]).ids)]
			else:
				record.employee_domain = [(6, 0, [])]

	@api.model
	def create(self, values):
		loan_count = self.env['hr.loan'].search_count(
			[('employee_id', '=', values['employee_id']), ('state', '=', 'approve'),
			 ('balance_amount', '!=', 0)])
		if loan_count:
			raise ValidationError(_("The employee has already a pending installment"))
		else:
			values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
			res = super(HrLoan, self).create(values)
			return res

	
	def compute_installment(self):
		"""This automatically creates the installment the employee needs to pay to the company
		based on the payment start date and the number of installments.
		"""
		for loan in self:
			loan.loan_lines.unlink()
			outstanding = loan.loan_amount
			date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
			principle = loan.loan_amount / loan.installment
	
			for i in range(1, loan.installment + 1):

				interest = (outstanding * (loan.interest_amount / 100)) if loan.interest_type == 'with_interest' else 0
				loan_line_vals = {
					'date': date_start,
					'principle': principle,
					'interest_aomunt': interest,
					'employee_id': loan.employee_id.id,
					'amount' : principle + interest,
					'loan_id': loan.id
				}
				self.env['hr.loan.line'].create(loan_line_vals)
	
				
				outstanding -= principle
				date_start += relativedelta(months=1)
	
			loan._compute_loan_amount()
	
		return True

	def action_refuse(self):
		return self.write({'state': 'refuse'})


	def action_cancel(self):
		self.write({'state': 'cancel'})

	def action_approve(self):
		for data in self:
			if not data.loan_lines:
				raise ValidationError(_("Please Compute installment"))
			else:
				approval_cat_id = self.env.ref('hc_loan_management.approval_category_loan_approval')
				approval_request = self.env['approval.request'].create({
					'request_owner_id': self.env.user.id,
					'category_id': approval_cat_id.id,
					'name': self.employee_id.name,
					'partner_id':  self.employee_id.id,
					'loan_ids' : self.id,

				})
				data.write({'approval_request': approval_request.id, 'approve_button_hide' : True})



	def unlink(self):
		for loan in self:
			if loan.state not in ('draft', 'cancel'):
				raise UserError(
					'You cannot delete a loan which is not in draft or cancelled state')
		return super(HrLoan, self).unlink()


class InstallmentLine(models.Model):
	_name = "hr.loan.line"
	_description = "Installment Line"

	date = fields.Date(string="Payment Date", required=True, help="Date of the payment")
	employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
	amount = fields.Float(string="Amount", help="Amount")
	paid = fields.Boolean(string="Paid", help="Paid")
	loan_id = fields.Many2one('hr.loan', string="Loan Ref.", help="Loan")
	principle = fields.Float(string="Principle", required=True, help="Amount")
	interest_aomunt = fields.Float(string="Interest Amount", required=True, help="Amount")


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	def _compute_employee_loans(self):
		"""This compute the loan amount and total loans count of an employee.
			"""
		self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

	loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')



class ApprovalRequest(models.Model):
	_inherit = "approval.request"

	loan_ids = fields.Many2one("hr.loan", string='Registration ID')
	
	def _set_approved_states(self):
		if self.loan_ids:
			self.loan_ids.write({'state': 'approve'})


	def action_approve(self):
		super(ApprovalRequest, self).action_approve()
		approval_cat_id = self.env.ref('hc_loan_management.approval_category_loan_approval')
		if self.category_id.id == approval_cat_id.id:
			self._set_approved_states()
		
		