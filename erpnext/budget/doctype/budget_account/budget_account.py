# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class BudgetAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		account_number: DF.Data | None
		april: DF.Currency
		august: DF.Currency
		br_april: DF.Data | None
		br_august: DF.Data | None
		br_december: DF.Data | None
		br_february: DF.Data | None
		br_january: DF.Data | None
		br_july: DF.Data | None
		br_june: DF.Data | None
		br_march: DF.Data | None
		br_may: DF.Data | None
		br_november: DF.Data | None
		br_october: DF.Data | None
		br_september: DF.Data | None
		bs_april: DF.Data | None
		bs_august: DF.Data | None
		bs_december: DF.Data | None
		bs_february: DF.Data | None
		bs_january: DF.Data | None
		bs_july: DF.Data | None
		bs_june: DF.Data | None
		bs_march: DF.Data | None
		bs_may: DF.Data | None
		bs_november: DF.Data | None
		bs_october: DF.Data | None
		bs_september: DF.Data | None
		budget_amount: DF.Currency
		budget_check: DF.Literal["", "Stop", "Ignore"]
		budget_received: DF.Currency
		budget_sent: DF.Currency
		budget_type: DF.Link | None
		december: DF.Currency
		february: DF.Currency
		initial_budget: DF.Currency
		january: DF.Currency
		july: DF.Currency
		june: DF.Currency
		march: DF.Currency
		may: DF.Currency
		november: DF.Currency
		october: DF.Currency
		parent: DF.Data
		parent_account: DF.Link | None
		parentfield: DF.Data
		parenttype: DF.Data
		project_code: DF.Link | None
		project_name: DF.Data | None
		sb_april: DF.Data | None
		sb_august: DF.Data | None
		sb_december: DF.Data | None
		sb_february: DF.Data | None
		sb_january: DF.Data | None
		sb_july: DF.Data | None
		sb_june: DF.Data | None
		sb_march: DF.Data | None
		sb_may: DF.Data | None
		sb_november: DF.Data | None
		sb_october: DF.Data | None
		sb_september: DF.Data | None
		september: DF.Currency
		source_of_fund: DF.Link | None
		source_of_fund_name: DF.Data | None
		supplementary_budget: DF.Currency
	# end: auto-generated types
	pass
