# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
import datetime
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_months, flt, fmt_money, get_last_day, getdate, get_first_day

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year
# from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class BudgetError(frappe.ValidationError):
	pass

class DuplicateBudgetError(frappe.ValidationError):
	pass


class Budget(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.budget.doctype.budget_account.budget_account import BudgetAccount
		from frappe.types import DF

		accounts: DF.Table[BudgetAccount]
		action_if_accumulated_monthly_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_accumulated_monthly_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_mr: DF.Literal["", "Stop", "Warn", "Ignore"]
		action_if_annual_budget_exceeded_on_po: DF.Literal["", "Stop", "Warn", "Ignore"]
		actual_total: DF.Currency
		amended_from: DF.Link | None
		applicable_on_booking_actual_expenses: DF.Check
		applicable_on_material_request: DF.Check
		applicable_on_purchase_order: DF.Check
		approved_budget: DF.Currency
		branch: DF.Link | None
		budget_against: DF.Literal["Cost Center"]
		budget_proposal: DF.Link | None
		budget_type: DF.Data | None
		business_activity: DF.Link | None
		company: DF.Link
		cost_center: DF.Link
		deviation: DF.Percent
		fiscal_year: DF.Link
		initial_budget: DF.Currency
		initial_total: DF.Currency
		monthly_distribution: DF.Link | None
		posting_date: DF.Date
		supp_total: DF.Currency
		withdrawal_budget: DF.Currency
	# end: auto-generated types
	def autoname(self):
		self.name = make_autoname(
			#self.get(frappe.scrub(self.budget_against)) + "/" + self.fiscal_year + "/.###"
			"BUD" + "/" + self.fiscal_year + "/.###"
		)

	def validate(self):
		if not self.get(frappe.scrub(self.budget_against)):
			frappe.msgprint(_("{0} is mandatory").format(self.budget_against), raise_exception=True)
		self.validate_duplicate()
		self.validate_accounts()
		self.set_null_value()
		self.validate_applicable_for()
		self.set_initial_budget()
		self.calculate_budget()
		self.calculate_totals()
		# validate_workflow_states(self)

	def validate_duplicate(self):
		budget_against_field = frappe.scrub(self.budget_against)
		budget_against = self.get(budget_against_field)

		accounts = [d.account for d in self.accounts] or []
		existing_budget = frappe.db.sql(
			"""
			select
				b.name, ba.account from `tabBudget` b, `tabBudget Account` ba
			where
				ba.parent = b.name and b.docstatus < 2 and b.company = %s and %s=%s and
				b.fiscal_year=%s and b.name != %s and ba.account in (%s) """
			% ("%s", budget_against_field, "%s", "%s", "%s", ",".join(["%s"] * len(accounts))),
			(self.company, budget_against, self.fiscal_year, self.name) + tuple(accounts),
			as_dict=1)
		if existing_budget:
			for d in existing_budget:
				frappe.msgprint(
					_(
						"Another Budget record '{0}' already exists against {1} '{2}' and account '{3}' for fiscal year {4}"
					).format(d.name, self.budget_against, budget_against, d.account, self.fiscal_year),raise_exception=True
				)

	def validate_accounts(self):
		account_list = []
		for d in self.get("accounts"):
			if d.account:
				account_details = frappe.db.get_value(
					"Account", d.account, ["is_group", "company", "report_type"], as_dict=1
				)

				if account_details.is_group:
					frappe.msgprint(_("Budget cannot be assigned against Group Account {0}").format(d.account), raise_exception=True)
				elif account_details.company != self.company:
					frappe.msgprint(_("Account {0} does not belongs to company {1}").format(d.account, self.company), raise_exception=True)
				'''
				elif account_details.report_type != "Profit and Loss":
					frappe.throw(
						_("Budget cannot be assigned against {0}, as it's not an Income or Expense account").format(
							d.account
						)
					)
				'''

				if d.account in account_list:
					frappe.msgprint(_("Account {0} has been entered multiple times").format(d.account), raise_exception=True)
				else:
					account_list.append(d.account)

	def set_null_value(self):
		if self.budget_against == "Cost Center":
			self.project = None
		else:
			self.cost_center = None

	def validate_applicable_for(self):
		if self.applicable_on_material_request and not (
			self.applicable_on_purchase_order and self.applicable_on_booking_actual_expenses
		):
			frappe.msgprint(
				_("Please enable Applicable on Purchase Order and Applicable on Booking Actual Expenses"), raise_exception=True
			)

		elif self.applicable_on_purchase_order and not (self.applicable_on_booking_actual_expenses):
			frappe.msgprint(_("Please enable Applicable on Booking Actual Expenses"), raise_exception=True)

		elif not (
			self.applicable_on_material_request
			or self.applicable_on_purchase_order
			or self.applicable_on_booking_actual_expenses
		):
			self.applicable_on_booking_actual_expenses = 1

	def calculate_budget(self):
		if self.accounts:
			for acc in self.accounts:
				acc.budget_amount = flt(acc.initial_budget) + flt(acc.supplementary_budget) + flt(acc.budget_received) - flt(acc.budget_sent)
				acc.db_set("budget_amount", acc.budget_amount)

	def calculate_totals(self): 
		total_initial = 0
		total_actual = 0
		total_supplementary = 0
		if self.accounts:
			for item in self.accounts:
				total_initial += flt(item.initial_budget)
				total_actual += flt(item.budget_amount)
				total_supplementary += flt(item.supplementary_budget)

			self.initial_total = total_initial
			self.actual_total = total_actual
			self.supp_total = total_supplementary
	
	@frappe.whitelist()
	def set_initial_budget(self):
		for d in self.accounts:
			initial_budget = flt(d.january) + flt(d.february) + flt(d.march) + flt(d.april)+ flt(d.may) +flt(d.june) +flt(d.july) +flt(d.august) + flt(d.september) +flt(d.october) +flt(d.november) +flt(d.december)
			d.db_set("initial_budget", initial_budget)
			d.db_set("budget_amount", flt(initial_budget) + flt(d.supplementary_budget) + flt(d.budget_received) - flt(d.budget_sent))
	@frappe.whitelist()
	def get_accounts(self):
		# Fetch parent account from Budget Settings
		parent_account = frappe.db.get_single_value("Budget Settings", "budget_account")

		if not parent_account:
			frappe.throw(_("Please set Budget Account Parent in Budget Settings"))

		# Get lft and rgt of parent account
		parent = frappe.db.get_value(
			"Account",
			parent_account,
			["lft", "rgt"],
			as_dict=True
		)

		if not parent:
			frappe.throw(_("Parent Account not found: {0}").format(parent_account))

		# Optional budget type filter
		condition = ""
		values = {
			"company": self.company,
			"lft": parent.lft,
			"rgt": parent.rgt
		}

		if self.budget_type:
			condition = " AND a.budget_type = %(budget_type)s"
			values["budget_type"] = self.budget_type

		# Fetch all ledger accounts under parent account
		account_list = frappe.db.sql("""
			SELECT
				a.parent_account,
				a.name AS account,
				a.account_name,
				a.account_number,
				a.budget_type
			FROM `tabAccount` a
			WHERE a.company = %(company)s
			  AND a.lft > %(lft)s
			  AND a.rgt < %(rgt)s
			  AND a.is_group = 0
			  AND (a.freeze_account IS NULL OR a.freeze_account != 'Yes')
			  {condition}
			ORDER BY a.lft
		""".format(condition=condition), values, as_dict=True)

		# Remove old rows from Budget Accounts child table
		self.set("accounts", [])

		# Add fetched accounts into child table
		for acc in account_list:
			row = self.append("accounts", {})
			row.account = acc.account
			row.account_code = acc.account_number
			row.budget_type = acc.budget_type	
	
def delete_committed_consumed_budget(reference=None, reference_no=None):
	if reference and reference_no:
		frappe.db.sql("""Delete from `tabCommitted Budget` 
						where reference_type='{reference_type}' 
						and reference_no='{reference_no}'
						""".format(reference_type=reference, reference_no=reference_no))
		frappe.db.sql("""Delete from `tabConsumed Budget` 
						where reference_type='{reference_type}' 
						and reference_no='{reference_no}'
						""".format(reference_type=reference, reference_no=reference_no))

def validate_expense_against_budget(args, throw_error=True):
	args = frappe._dict(args)
	if args.is_cancelled:
		delete_committed_consumed_budget(args.voucher_type, args.voucher_no)
		return
	error=[]
	if args.get("company") and not args.fiscal_year:
		args.fiscal_year = get_fiscal_year(args.get("posting_date"), company=args.get("company"))[0]
		frappe.flags.exception_approver_role = frappe.get_cached_value(
			"Company", args.get("company"), "exception_budget_approver_role"
		)

	if not args.account:
		args.account = args.get("expense_account")

	if not args.get("account") and args.item_code:
		args.account = get_item_details(args)
	if not args.cost_center:
		frappe.throw("Cost Center is missing for budget check")

	if not args.account:
		frappe.msgprint("Budget Head/Account is missing. Please provide account to check budget", raise_exception=True)

	account_dtl = frappe.get_doc("Account", args.account)
	account_type = account_dtl.account_type
	
	if not account_type:
		frappe.throw("Account Type missing for Budget account <b>{}</b>".format(args.account))

	if account_dtl.ignore_budget_check:
		return
	'''
	if not frappe.db.exists("Budget Settings Account Types", {"parent":"Budget Settings","account_type":account_type}):
		frappe.throw("Budget check against account <b>{}</b> is not allowed as the Account Type is {}. \
						Check Budget Settings for allowed account type".format(args.account, account_type))
	'''
	""" avoid budget check at MR """
	# if frappe.db.get_single_value("Budget Settings", "budget_commit_on") != "Material Request":
	for budget_against in ["project", "cost_center"] + get_accounting_dimensions():
		if (
			args.get(budget_against)
			and args.account
			and frappe.db.get_value("Account", args.account, "account_type") in ["Expense Account","Fixed Asset"]
		):
			doctype = frappe.unscrub(budget_against)
			args.budget_against_field = budget_against
			args.budget_against_doctype = doctype
			if args.project:
				condition = " and b.project = '{}'".format(args.project)
			else:
				bud_acc_dtl = frappe.get_doc("Account", args.account)
				if bud_acc_dtl.is_centralized_budget:
					budget_cost_center = bud_acc_dtl.cost_center
				else:
					#Check Budget Cost for child cost centers
					cc_doc = frappe.get_doc("Cost Center", args.cost_center)
					#budget_cost_center = cc_doc.budget_cost_center if cc_doc.use_budget_from_parent else args.cost_center
				condition = " and b.cost_center='{}'".format(args.cost_center)
				
			args.is_tree = False
			if not args.project:
				args.committed_cost_center = args.cost_center
				args.cost_center = args.cost_center
			
			budget_records = frappe.db.sql(
				"""
				select
					b.{budget_against_field} as budget_against, ba.budget_amount, b.monthly_distribution,
					ifnull(b.applicable_on_material_request, 0) as for_material_request,
					ifnull(applicable_on_purchase_order, 0) as for_purchase_order,
					ifnull(applicable_on_booking_actual_expenses,0) as for_actual_expenses,
					b.action_if_annual_budget_exceeded, b.action_if_accumulated_monthly_budget_exceeded,
					b.action_if_annual_budget_exceeded_on_mr, b.action_if_accumulated_monthly_budget_exceeded_on_mr,
					b.action_if_annual_budget_exceeded_on_po, b.action_if_accumulated_monthly_budget_exceeded_on_po
				from
					`tabBudget` b, `tabBudget Account` ba
				where
					b.name=ba.parent and b.fiscal_year={fiscal_year}
					and ba.account="{account}" and b.docstatus=1
					{condition}
			""".format(
					condition=condition, budget_against_field=budget_against,
				fiscal_year=args.fiscal_year, account=args.account),
				as_dict=True,
			)  # nosec
	
			
			if budget_records:
				validate_budget_records(args, error, budget_records, throw_error)
			elif throw_error:
				frappe.msgprint(_("Budget allocation not available for <b>%s </b> in %s <b>%s</b>" % (
								args.account, budget_against, frappe.db.escape(args.get(budget_against))
							)), raise_exception=True
						)
			else:
				error.append("Budget allocation not available for <b>%s </b> in %s <b>%s</b>" % (
								args.account, budget_against, frappe.db.escape(args.get(budget_against))
							))
				return error[0]
			if len(error)>0:
				return error[0]
				
	commit_budget(args)

def validate_budget_records(args, error, budget_records, throw_error):

	for budget in budget_records:
		amount = get_amount(args, budget)
		yearly_action, monthly_action = get_actions(args, budget)
		monthly_budget_check = frappe.db.get_single_value("Budget Settings","monthly_budget_check")
		if monthly_budget_check:
			budget_account = args.expense_account
			if not budget_account:
				budget_account = args.account
			transaction_date = args.posting_date
			budget_amount = get_accumulated_monthly_budget(
				args.cost_center, budget_account, transaction_date, args.amount, args.fiscal_year
			)
			args["month_end_date"] = get_last_day(args.posting_date)

			compare_expense_with_budget(
				args, error, budget_amount, _("Accumulated Monthly"), monthly_action, budget.budget_against, amount, throw_error
			)
		else:
			budget_amount = budget.budget_amount
			if yearly_action in ("Stop", "Warn"):
				compare_expense_with_budget(
					args, error, flt(budget.budget_amount), _("Annual"), yearly_action, budget.budget_against, amount, throw_error
				)

def compare_expense_with_budget(args, error, budget_amount, action_for, action, budget_against, amount=0, throw_error=None):
	actual_expense = amount or args.amount
	if args.project:
		condition = " and cb.project = '{}'".format(budget_against)
	else:
		condition = " and cb.cost_center = {}".format(frappe.db.escape(budget_against))
	args.fiscal_year = args.fiscal_year if args.fiscal_year else str(args.posting_date)[0:4]
	start_date = get_first_day(args.posting_date)
	end_date = get_last_day(args.posting_date)
	committed = frappe.db.sql("""select SUM(cb.amount) as total 
								from `tabCommitted Budget` cb 
								where cb.account={account} 
								{condition} 
								and cb.reference_date between '{start_date}' and '{end_date}'""".format(condition=condition, 
							account=frappe.db.escape(args.account), cost_center=args.cost_center, start_date=start_date, 
							end_date=end_date), as_dict=True)
	consumed = frappe.db.sql("""select SUM(cb.amount) as total 
								from `tabConsumed Budget` cb 
								where cb.account={account}
								{condition} 
								and cb.reference_date between '{start_date}' and '{end_date}'""".format(condition=condition, 
							account=frappe.db.escape(args.account), cost_center=args.cost_center, start_date=start_date, 
							end_date=end_date), as_dict=True)
	if consumed and committed:
		if flt(consumed[0].total) > flt(committed[0].total):
			committed = consumed
		total_expense_amount = flt(committed[0].total) + flt(actual_expense)
		if frappe.db.get_single_value("Budget Settings","allow_budget_deviation"):
			deviation_percent = frappe.db.get_single_value("Budget Settings","deviation")
			if deviation_percent > 0:
				budget_amount = budget_amount  + (deviation_percent*budget_amount)/100
		available_budget = 	flt(budget_amount) - flt(committed[0].total)
	else:
		available_budget = flt(budget_amount)
		total_expense_amount = flt(actual_expense)

	if total_expense_amount > budget_amount:
		diff = total_expense_amount - budget_amount
		currency = frappe.get_cached_value("Company", args.company, "default_currency")
		message = ''
		if args.doctype in ("Purchase Order", "Purchase Invoice"):
			message = f" until #Row. {args.idx} with Item Code #{args.item_code}."

		msg = _("{0} Budget for Account {1} against {2} {3} is {4} and available budget is {5} Including (Supplementary Budget,Budget Received,Budget Sent). It exceed by {6}{7}").format(
			_(action_for),
			frappe.bold(args.account),
			args.budget_against_field,
			frappe.bold(budget_against),
			frappe.bold(fmt_money(budget_amount, currency=currency)),
			frappe.bold(fmt_money(available_budget, currency=currency)),
			frappe.bold(fmt_money(diff, currency=currency)),
			message,
		)

		if (
			frappe.flags.exception_approver_role
			and frappe.flags.exception_approver_role in frappe.get_roles(frappe.session.user)
		):
			action = "Warn"
		
		error.append(msg)
		if throw_error:
			if action == "Stop":
				frappe.msgprint(msg, raise_exception=True)
				frappe.throw(str(msg))
			else:
				frappe.msgprint(msg, indicator="orange")
				frappe.throw(str(msg))
		else:
			return error[0]

def commit_budget(args):
	amount = args.amount if args.amount else args.debit
	if frappe.db.get_single_value("Budget Settings", "budget_commit_on") == args.doctype and args.amount > 0:
		account_types = [d.account_type for d in frappe.get_all("Budget Settings Account Types", fields='account_type')]
		if frappe.db.get_value("Account", args.account, "account_type") in account_types:
			doc = frappe.get_doc(
				{
					"doctype": "Committed Budget",
					"account": args.account,
					"cost_center": args.cost_center,
					"committed_cost_center": args.committed_cost_center,
					"project": args.project,
					"reference_type": args.doctype,
					"reference_no": args.parent,
					"reference_date": args.posting_date,
					"reference_id": args.name,
					"amount": flt(amount,2),
					"item_code": args.item_code,
					"company": args.company
				}
			)
			doc.submit()

def get_actions(args, budget):
	yearly_action = budget.action_if_annual_budget_exceeded
	monthly_action = budget.action_if_accumulated_monthly_budget_exceeded

	if args.get("doctype") == "Material Request" and budget.for_material_request:
		yearly_action = budget.action_if_annual_budget_exceeded_on_mr
		monthly_action = budget.action_if_accumulated_monthly_budget_exceeded_on_mr

	elif args.get("doctype") == "Purchase Order" and budget.for_purchase_order:
		yearly_action = budget.action_if_annual_budget_exceeded_on_po
		monthly_action = budget.action_if_accumulated_monthly_budget_exceeded_on_po

	return yearly_action, monthly_action


def get_amount(args, budget):
	amount = 0
	if args.amount:
		amount = args.amount
	else:
		amount = args.debit
	return amount


def get_requested_amount(args, budget):
	item_code = args.get("item_code")
	condition = get_other_condition(args, budget, "Material Request")

	data = frappe.db.sql(
		""" select ifnull((sum(child.stock_qty - child.ordered_qty) * rate), 0) as amount
		from `tabMaterial Request Item` child, `tabMaterial Request` parent where parent.name = child.parent and
		child.item_code = %s and parent.docstatus = 1 and child.stock_qty > child.ordered_qty and {0} and
		parent.material_request_type = 'Purchase' and parent.status != 'Stopped'""".format(
			condition
		),
		item_code,
		as_list=1,
	)

	return data[0][0] if data else 0


def get_ordered_amount(args, budget):
	item_code = args.get("item_code")
	condition = get_other_condition(args, budget, "Purchase Order")

	data = frappe.db.sql(
		""" select ifnull(sum(child.amount - child.billed_amt), 0) as amount
		from `tabPurchase Order Item` child, `tabPurchase Order` parent where
		parent.name = child.parent and child.item_code = %s and parent.docstatus = 1 and child.amount > child.billed_amt
		and parent.status != 'Closed' and {0}""".format(
			condition
		),
		item_code,
		as_list=1,
	)

	return data[0][0] if data else 0


def get_other_condition(args, budget, for_doc):
	condition = "expense_account = '%s'" % (args.expense_account)
	budget_against_field = args.get("budget_against_field")

	if budget_against_field and args.get(budget_against_field):
		condition += " and child.%s = '%s'" % (budget_against_field, args.get(budget_against_field))

	if args.get("fiscal_year"):
		date_field = "schedule_date" if for_doc == "Material Request" else "transaction_date"
		start_date, end_date = frappe.db.get_value(
			"Fiscal Year", args.get("fiscal_year"), ["year_start_date", "year_end_date"]
		)

		condition += """ and parent.%s
			between '%s' and '%s' """ % (
			date_field,
			start_date,
			end_date,
		)

	return condition


def get_actual_expense(args):
	if not args.budget_against_doctype:
		args.budget_against_doctype = frappe.unscrub(args.budget_against_field)

	budget_against_field = args.get("budget_against_field")
	condition1 = " and gle.posting_date <= %(month_end_date)s" if args.get("month_end_date") else ""

	if args.is_tree:
		lft_rgt = frappe.db.get_value(
			args.budget_against_doctype, args.get(budget_against_field), ["lft", "rgt"], as_dict=1
		)

		args.update(lft_rgt)

		condition2 = """and exists(select name from `tab{doctype}`
			where lft>=%(lft)s and rgt<=%(rgt)s
			and name=gle.{budget_against_field})""".format(
			doctype=args.budget_against_doctype, budget_against_field=budget_against_field  # nosec
		)
	else:
		condition2 = """and exists(select name from `tab{doctype}`
		where name=gle.{budget_against} and
		gle.{budget_against} = %({budget_against})s)""".format(
			doctype=args.budget_against_doctype, budget_against=budget_against_field
		)

	amount = flt(
		frappe.db.sql(
			"""
		select sum(gle.debit) - sum(gle.credit)
		from `tabGL Entry` gle
		where gle.account=%(account)s
			{condition1}
			and gle.fiscal_year=%(fiscal_year)s
			and gle.company=%(company)s
			and gle.docstatus=1
			{condition2}
	""".format(
				condition1=condition1, condition2=condition2
			),
			(args),
		)[0][0]
	)  # nosec

	return amount

from datetime import datetime
def get_accumulated_monthly_budget(cost_center, budget_account, transaction_date, amount, fiscal_year):
	# mydate = datetime.strptime(transaction_date, '%Y-%m-%d')
	mydate = datetime.fromisoformat(str(transaction_date))
	month = mydate.month
	if frappe.db.get_value("Account", budget_account, "ignore_budget_check"):
		return
	budget_against = frappe.db.get_single_value("Budget Settings","budget_against")
	cond = ""
	if budget_against == "Cost Center":
		cond += ''' and b.budget_against = "{}" and b.cost_center = "{}" '''.format(budget_against, cost_center)
	else:
		cond += ''' and b.budget_against = "{}" '''.format(budget_against)
	budget_amount = frappe.db.sql('''select b.action_if_annual_budget_exceeded as annual_action, ba.budget_check,\
					ba.budget_amount, b.deviation, \
					ba.january, ba.february, ba.march, ba.april, ba.may, ba.june, ba.july, ba.august, ba.september, ba.october, ba.november, ba.december\
					from `tabBudget` b, `tabBudget Account` ba \
					where b.docstatus = 1 \
					and ba.parent = b.name and ba.account= "{}" \
					and b.fiscal_year = "{}" {} '''.format(budget_account, str(transaction_date)[0:4], cond), as_dict=True)
	# frappe.throw(str(budget_amount))
	if month == 1:
		monthly_amount = budget_amount[0].january
		month_name = "January"
	elif month == 2:
		monthly_amount = budget_amount[0].february
		month_name = "February"
	elif month == 3:
		monthly_amount = budget_amount[0].march
		month_name = "March"
	elif month == 4:
		monthly_amount = budget_amount[0].april
		month_name = "April"
	elif month == 5:
		monthly_amount = budget_amount[0].may
		month_name = "May"
	elif month == 6:
		monthly_amount = budget_amount[0].june
		month_name = "June"
	elif month == 7:
		monthly_amount = budget_amount[0].july
		month_name = "July"
	elif month == 8:
		monthly_amount = budget_amount[0].august
		month_name = "August"
	elif month == 9:
		monthly_amount = budget_amount[0].september
		month_name = "September"
	elif month == 10:
		monthly_amount = budget_amount[0].october
		month_name = "October"
	elif month == 11:
		monthly_amount = budget_amount[0].november
		month_name = "November"
	else:
		monthly_amount = budget_amount[0].december
		month_name = "December"

	if transaction_date:
		month_first_date = get_first_day(transaction_date)
		month_last_date = get_last_day(transaction_date)
		supplement = flt(frappe.db.sql("""
				select sum(amount)
				from `tabSupplementary Details`
				where month = "{month}"
				and fiscal_year = "{fiscal_year}"
				and account="{account}"
				and cost_center="{cost_center}"
			""".format(from_date=month_first_date, to_date=month_last_date,account = budget_account, month = month_name, cost_center=cost_center, fiscal_year=fiscal_year))[0][0],2)
		monthly_received = frappe.db.sql("""
				select sum(amount)
				from `tabReappropriation Details`
				where fiscal_year = "{fiscal_year}"
				and to_account="{account}"
				and to_cost_center="{cost_center}"
				and to_month = "{month}"
			""".format(from_date=month_first_date, to_date=month_last_date, month = month_name, account = budget_account, cost_center=cost_center, fiscal_year=fiscal_year))[0][0]
		monthly_sent = frappe.db.sql("""
				select sum(amount)
				from `tabReappropriation Details`
				where fiscal_year = "{fiscal_year}"
				and from_account="{account}"
				and from_cost_center="{cost_center}"
				and from_month = "{month}"
			""".format(from_date=month_first_date, to_date=month_last_date,month = month_name, account = budget_account, cost_center=cost_center, fiscal_year=fiscal_year))[0][0]
		adjustment = flt(supplement,2) + flt(monthly_received,2) - flt(monthly_sent,2)
	if adjustment:
		sum =flt(adjustment) + flt(monthly_amount)
		return sum
	else:
		return monthly_amount


def get_item_details(args):
	cost_center, expense_account = None, None

	if not args.get("company"):
		return cost_center, expense_account

	if args.item_code:
		item_defaults = frappe.db.get_value(
			"Item Default",
			{"parent": args.item_code, "company": args.get("company")},
			["buying_cost_center", "expense_account"],
		)
		if item_defaults:
			cost_center, expense_account = item_defaults

	if not (cost_center and expense_account):
		for doctype in ["Item Group", "Company"]:
			data = get_expense_cost_center(doctype, args)

			if not cost_center and data:
				cost_center = data[0]

			if not expense_account and data:
				expense_account = data[1]

			if cost_center and expense_account:
				return cost_center, expense_account

	return cost_center, expense_account


def get_expense_cost_center(doctype, args):
	if doctype == "Item Group":
		return frappe.db.get_value(
			"Item Default",
			{"parent": args.get(frappe.scrub(doctype)), "company": args.get("company")},
			["buying_cost_center", "expense_account"],
		)
	else:
		return frappe.db.get_value(
			doctype, args.get(frappe.scrub(doctype)), ["cost_center", "default_expense_account"]
		)