# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class BudgetSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.budget.doctype.budget_settings_account_types.budget_settings_account_types import BudgetSettingsAccountTypes
		from erpnext.budget.doctype.budget_transaction.budget_transaction import BudgetTransaction
		from frappe.types import DF

		allow_budget_deviation: DF.Check
		allowed_account_types: DF.Table[BudgetSettingsAccountTypes]
		allowed_transactions: DF.Table[BudgetTransaction]
		budget_account: DF.Link | None
		budget_against: DF.Literal["Cost Center", "Project"]
		budget_commit_on: DF.Literal["Purchase Order", "Material Request"]
		deviation: DF.Percent
		monthly_budget_check: DF.Check
	# end: auto-generated types
	pass
