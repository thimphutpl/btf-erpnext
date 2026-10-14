# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class ForexTranslationRevaluationAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		account_currency: DF.Link | None
		balance_in_account_currency: DF.Currency
		balance_in_base_currency: DF.Currency
		current_balance_in_base_currency: DF.Float
		current_exchange_rate: DF.Float
		gain_loss: DF.Float
		gainloss_btn: DF.Float
		new_balance_in_account_currency: DF.Currency
		new_balance_in_base_currency: DF.Float
		new_exchange_rate: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		zero_balance: DF.Check
	# end: auto-generated types

	pass
