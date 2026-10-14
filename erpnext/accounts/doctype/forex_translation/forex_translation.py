# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
#from erpnext.accounts.doctype.forex_translation_item.forex_translation_item import ForexTranslationItem

class ForexTranslation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.accounts.doctype.forex_translation_item.forex_translation_item import ForexTranslationItem
		from frappe.types import DF

		amended_from: DF.Link | None
		fiscal_year: DF.Link | None
		items: DF.Table[ForexTranslationItem]
	# end: auto-generated types
	
	@frappe.whitelist()
	def get_currency(self):
		frappe.throw("pl")
