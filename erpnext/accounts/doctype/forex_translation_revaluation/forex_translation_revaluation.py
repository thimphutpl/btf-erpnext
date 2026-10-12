# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.query_builder import Criterion, Order
from frappe.query_builder.functions import NullIf, Sum
from frappe.utils import flt, get_link_to_form

import erpnext
from erpnext.accounts.doctype.journal_entry.journal_entry import get_balance_on
from erpnext.accounts.utils import get_currency_precision
from erpnext.setup.utils import get_exchange_rate


class ForexTranslationRevaluation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.accounts.doctype.forex_translation_revaluation_account.forex_translation_revaluation_account import ForexTranslationRevaluationAccount
		from frappe.types import DF

		accounts: DF.Table[ForexTranslationRevaluationAccount]
		amended_from: DF.Link | None
		branch: DF.Link | None
		company: DF.Link
		from_date: DF.Date
		gain_loss_booked: DF.Currency
		gain_loss_unbooked: DF.Currency
		posting_date: DF.Date
		rounding_loss_allowance: DF.Float
		to_date: DF.Date
		total_gain_loss: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_rounding_loss_allowance()
		#self.set_total_gain_loss()

	def validate_rounding_loss_allowance(self):
		if not (
			self.rounding_loss_allowance >= 0
			and self.rounding_loss_allowance < 1
		):
			frappe.throw(
				_("Rounding Loss Allowance should be between 0 and 1")
			)

	def set_total_gain_loss(self):
		total_gain_loss = 0
		gain_loss_booked = 0
		gain_loss_unbooked = 0

		for d in self.accounts:
			if not d.zero_balance:
				d.gain_loss = flt(
					d.new_balance_in_base_currency,
					d.precision("new_balance_in_base_currency"),
				) - flt(
					d.balance_in_base_currency,
					d.precision("balance_in_base_currency"),
				)

			if d.zero_balance:
				gain_loss_booked += flt(
					d.gain_loss,
					d.precision("gain_loss"),
				)
			else:
				gain_loss_unbooked += flt(
					d.gain_loss,
					d.precision("gain_loss"),
				)

			total_gain_loss += flt(
				d.gain_loss,
				d.precision("gain_loss"),
			)

		self.gain_loss_booked = gain_loss_booked
		self.gain_loss_unbooked = gain_loss_unbooked

		self.total_gain_loss = flt(
			total_gain_loss,
			self.precision("total_gain_loss"),
		)

	def validate_mandatory(self):
		if not (self.company and self.posting_date):
			frappe.throw(
				_("Please select Company and Posting Date to getting entries")
			)

	def before_submit(self):
		self.remove_accounts_without_gain_loss()

	def remove_accounts_without_gain_loss(self):
		self.accounts = [
			account
			for account in self.accounts
			if account.gain_loss
		]

		if not self.accounts:
			frappe.throw(
				_("At least one account with exchange gain or loss is required")
			)

		frappe.msgprint(
			_("Removing rows without exchange gain or loss"),
			alert=True,
			indicator="yellow",
		)

	def on_cancel(self):
		self.ignore_linked_doctypes = "GL Entry"

	@frappe.whitelist()
	def check_journal_entry_condition(self):
		exchange_gain_loss_account = (
			self.get_for_unrealized_gain_loss_account()
		)

		jea = qb.DocType("Journal Entry Account")

		journals = (
			qb.from_(jea)
			.select(jea.parent)
			.distinct()
			.where(
				(jea.reference_type == "Exchange Rate Revaluation")
				& (jea.reference_name == self.name)
				& (jea.docstatus == 1)
			)
			.run()
		)

		if journals:
			gle = qb.DocType("GL Entry")

			total_amt = (
				qb.from_(gle)
				.select(
					(Sum(gle.credit) - Sum(gle.debit)).as_(
						"total_amount"
					)
				)
				.where(
					(gle.voucher_type == "Journal Entry")
					& (gle.voucher_no.isin(journals))
					& (gle.account == exchange_gain_loss_account)
					& (gle.is_cancelled == 0)
				)
				.run()
			)

			if (
				total_amt
				and total_amt[0][0] != self.total_gain_loss
			):
				return True

			return False

		return True

	def fetch_and_calculate_accounts_data(self):
		accounts = self.get_accounts_data()

		if accounts:
			for acc in accounts:
				self.append("accounts", acc)

	@frappe.whitelist()
	def get_accounts_data(self):
	
		
		self.validate_mandatory()
		
		account_details = self.get_account_balance_from_gle(
			company=self.company,
			posting_date=self.posting_date,
			from_date=self.from_date,
			to_date=self.to_date,
			account=None,
			party_type=None,
			party=None,
			rounding_loss_allowance=self.rounding_loss_allowance,
		)
		

		accounts_with_new_balance = self.calculate_new_account_balance(
			company=self.company,
			posting_date=self.posting_date,
			account_details=account_details,

			# Used only for finding the latest Journal Entry current_rate.
			rate_upto_date=self.to_date,
		)

		if not accounts_with_new_balance:
			self.throw_invalid_response_message(account_details)

		return accounts_with_new_balance

	@staticmethod
	# def get_account_balance_from_gle(
	# 	company,
	# 	posting_date,
	# 	from_date,
	# 	to_date,
	# 	account,
	# 	party_type,
	# 	party,
	# 	rounding_loss_allowance,
	# ):
	# 	account_details = []
		
	# 	if company and posting_date:
	# 		company_currency = erpnext.get_company_currency(company)
			
	# 		acc = qb.DocType("Account")

	# 		if account:
	# 			accounts = [account]

	# 			account_currency_map = {
	# 				account: (
	# 					frappe.get_cached_value(
	# 						"Account",
	# 						account,
	# 						"account_currency",
	# 					)
	# 					or company_currency
	# 				)
	# 			}

	# 		else:
				
	# 			res = (
	# 				qb.from_(acc)
	# 				.select(
	# 					acc.name,
	# 					acc.account_currency,
	# 				)
	# 				.where(
	# 					acc.root_type.isin(
	# 						["Asset", "Liability"]
	# 					)
	# 					& (acc.company == company)
	# 				)
	# 				.orderby(acc.name)
	# 				.run(as_dict=True)
	# 			)

	# 			accounts = [
	# 				row.name
	# 				for row in res
	# 			]

	# 			account_currency_map = {
	# 				row.name: (
	# 					row.account_currency
	# 					or company_currency
	# 				)
	# 				for row in res
	# 			}

	# 		if accounts:
			
	# 			gle = qb.DocType("GL Entry")

	# 			conditions = []

	# 			conditions.append(
	# 				gle.account.isin(accounts)
	# 			)

	# 			conditions.append(
	# 				gle.posting_date.gte(from_date)
	# 			)

	# 			conditions.append(
	# 				gle.posting_date.lte(to_date)
	# 			)

	# 			conditions.append(
	# 				gle.is_cancelled == 0
	# 			)

	# 			conditions.append(
	# 				gle.company == company
	# 			)

	# 			if party_type:
	# 				conditions.append(
	# 					gle.party_type == party_type
	# 				)

	# 			if party:
	# 				conditions.append(
	# 					gle.party == party
	# 				)

	# 			gle_balances = (
	# 				qb.from_(gle)
	# 				.select(
	# 					gle.account,
	# 					gle.party_type,
	# 					gle.party,
	# 					gle.account_currency,
	# 					(
	# 						Sum(
	# 							gle.debit_in_account_currency
	# 						)
	# 						- Sum(
	# 							gle.credit_in_account_currency
	# 						)
	# 					).as_(
	# 						"balance_in_account_currency"
	# 					),
	# 					(
	# 						Sum(gle.debit)
	# 						- Sum(gle.credit)
	# 					).as_("balance"),
	# 				)
	# 				.where(
	# 					Criterion.all(conditions)
	# 				)
	# 				.groupby(
	# 					gle.account,
	# 					NullIf(gle.party_type, ""),
	# 					NullIf(gle.party, ""),
	# 				)
	# 				.run(as_dict=True)
	# 			)

	# 			balance_dict = {}

	# 			for bal in gle_balances:
	# 				key = (
	# 					bal.account,
	# 					bal.party_type or "",
	# 					bal.party or "",
	# 				)

	# 				balance_dict[key] = bal

	# 			currency_precision = (
	# 				get_currency_precision()
	# 			)

	# 			rounding_loss_allowance = flt(
	# 				rounding_loss_allowance
	# 			)

	# 			for acc_name in accounts:
	# 				key = (
	# 					acc_name,
	# 					"",
	# 					"",
	# 				)

	# 				if key in balance_dict:
	# 					bal = balance_dict[key]

	# 					balance_in_acct_currency = flt(
	# 						bal.balance_in_account_currency,
	# 						currency_precision,
	# 					)

	# 					balance = flt(
	# 						bal.balance,
	# 						currency_precision,
	# 					)

	# 					account_currency = (
	# 						bal.account_currency
	# 						or account_currency_map.get(
	# 							acc_name,
	# 							company_currency,
	# 						)
	# 					)

	# 					party_type_val = (
	# 						bal.party_type
	# 					)

	# 					party_val = bal.party

	# 				else:
	# 					balance_in_acct_currency = 0
	# 					balance = 0

	# 					account_currency = (
	# 						account_currency_map.get(
	# 							acc_name,
	# 							company_currency,
	# 						)
	# 					)

	# 					party_type_val = None
	# 					party_val = None

	# 				if (
	# 					abs(balance_in_acct_currency)
	# 					<= rounding_loss_allowance
	# 				):
	# 					balance_in_acct_currency = 0

	# 				if (
	# 					abs(balance)
	# 					<= rounding_loss_allowance
	# 				):
	# 					balance = 0

	# 				zero_balance = (
	# 					True
	# 					if (
	# 						balance == 0
	# 						or balance_in_acct_currency == 0
	# 					)
	# 					else False
	# 				)

	# 				account_details.append(
	# 					frappe._dict(
	# 						{
	# 							"account": acc_name,
	# 							"party_type": party_type_val,
	# 							"party": party_val,
	# 							"account_currency": (
	# 								account_currency
	# 							),
	# 							"balance_in_account_currency": (
	# 								balance_in_acct_currency
	# 							),
	# 							"balance": balance,
	# 							"zero_balance": (
	# 								zero_balance
	# 							),
	# 						}
	# 					)
	# 				)

	# 			# Add party-wise balances separately.
	# 			for bal in gle_balances:
	# 				if not (
	# 					bal.party_type
	# 					and bal.party
	# 				):
	# 					continue

	# 				existing_keys = {
	# 					(
	# 						row.account,
	# 						row.party_type or "",
	# 						row.party or "",
	# 					)
	# 					for row in account_details
	# 				}

	# 				key = (
	# 					bal.account,
	# 					bal.party_type,
	# 					bal.party,
	# 				)

	# 				if key in existing_keys:
	# 					continue

	# 				balance_in_acct_currency = flt(
	# 					bal.balance_in_account_currency,
	# 					currency_precision,
	# 				)

	# 				balance = flt(
	# 					bal.balance,
	# 					currency_precision,
	# 				)

	# 				if (
	# 					abs(balance_in_acct_currency)
	# 					<= rounding_loss_allowance
	# 				):
	# 					balance_in_acct_currency = 0

	# 				if (
	# 					abs(balance)
	# 					<= rounding_loss_allowance
	# 				):
	# 					balance = 0

	# 				zero_balance = (
	# 					True
	# 					if (
	# 						balance == 0
	# 						or balance_in_acct_currency == 0
	# 					)
	# 					else False
	# 				)

	# 				account_details.append(
	# 					frappe._dict(
	# 						{
	# 							"account": bal.account,
	# 							"party_type": bal.party_type,
	# 							"party": bal.party,
	# 							"account_currency": (
	# 								bal.account_currency
	# 								or account_currency_map.get(
	# 									bal.account,
	# 									company_currency,
	# 								)
	# 							),
	# 							"balance_in_account_currency": (
	# 								balance_in_acct_currency
	# 							),
	# 							"balance": balance,
	# 							"zero_balance": zero_balance,
	# 						}
	# 					)
	# 				)

	# 	frappe.throw(str(account_details))
	def get_account_balance_from_gle(
    company,
    posting_date,
    from_date,
    to_date,
    account,
    party_type,
    party,
    rounding_loss_allowance,
	):
		account_details = []

		if company and posting_date:
			company_currency = erpnext.get_company_currency(company)

			acc = qb.DocType("Account")

			if account:
				accounts = [account]

				account_currency_map = {
					account: (
						frappe.get_cached_value(
							"Account",
							account,
							"account_currency",
						)
						or company_currency
					)
				}

			else:
				res = (
					qb.from_(acc)
					.select(
						acc.name,
						acc.account_currency,
					)
					.where(
						acc.root_type.isin(
							["Asset", "Liability"]
						)
						& (acc.company == company)
					)
					.orderby(acc.name)
					.run(as_dict=True)
				)

				accounts = [row.name for row in res]

				account_currency_map = {
					row.name: (
						row.account_currency
						or company_currency
					)
					for row in res
				}

			if accounts:
				gle = qb.DocType("GL Entry")

				conditions = []

				conditions.append(
					gle.account.isin(accounts)
				)

				conditions.append(
					gle.posting_date.gte(from_date)
				)

				conditions.append(
					gle.posting_date.lte(to_date)
				)

				conditions.append(
					gle.is_cancelled == 0
				)

				conditions.append(
					gle.company == company
				)

				if party_type:
					conditions.append(
						gle.party_type == party_type
					)

				if party:
					conditions.append(
						gle.party == party
					)

				# ---- No Sum, No groupby ----
				# Fetch each GL Entry row with current_rate included.
				gle_rows = (
					qb.from_(gle)
					.select(
						gle.account,
						gle.party_type,
						gle.party,
						gle.account_currency,
						gle.debit_in_account_currency,
						gle.credit_in_account_currency,
						gle.debit,
						gle.credit,
						gle.current_rate,
					)
					.where(
						Criterion.all(conditions)
					)
					.orderby(
						gle.account,
						gle.posting_date,
					)
					.run(as_dict=True)
				)

				currency_precision = get_currency_precision()
				rounding_loss_allowance = flt(
					rounding_loss_allowance
				)

				for row in gle_rows:
					balance_in_acct_currency = flt(
						row.debit_in_account_currency
						- row.credit_in_account_currency,
						currency_precision,
					)

					balance = flt(
						row.debit - row.credit,
						currency_precision,
					)

					account_currency = (
						row.account_currency
						or account_currency_map.get(
							row.account,
							company_currency,
						)
					)

					if (
						abs(balance_in_acct_currency)
						<= rounding_loss_allowance
					):
						balance_in_acct_currency = 0

					if abs(balance) <= rounding_loss_allowance:
						balance = 0

					zero_balance = True if (
						balance == 0
						or balance_in_acct_currency == 0
					) else False

					account_details.append(
						frappe._dict(
							{
								"account": row.account,
								"party_type": row.party_type,
								"party": row.party,
								"account_currency": account_currency,
								"debit_in_account_currency": row.debit_in_account_currency,
								"credit_in_account_currency": row.credit_in_account_currency,
								"debit": row.debit,
								"credit": row.credit,
								"current_rate": row.current_rate,
								"balance_in_account_currency": balance_in_acct_currency,
								"balance": balance,
								"zero_balance": zero_balance,
							}
						)
					)

		#frappe.throw(str(account_details))

		return account_details

	@staticmethod
	def calculate_new_account_balance(
		company,
		posting_date,
		account_details,
		rate_upto_date=None,
	):
		accounts = []

		company_currency = (
			erpnext.get_company_currency(company)
		)

		precision = get_field_precision(
			frappe.get_meta(
				"Forex Translation Revaluation Account"
			).get_field(
				"new_balance_in_base_currency"
			),
			company_currency,
		)

		# Use Forex To Date when available.
		# This does not affect New Exchange Rate.
		rate_upto_date = (
			rate_upto_date
			or posting_date
		)

		current_rate_cache = {}

		def fetch_current_rate(d):
			cache_key = (
				d.account,
				d.party_type or "",
				d.party or "",
			)
			#frappe.throw(str(posting_date))
			if cache_key not in current_rate_cache:
				#frappe.throw(str(posting_date))
				current_rate_cache[cache_key] = (
					get_current_rate_from_journal_entry(
						company=company,
						account=d.account,
						# upto_date=rate_upto_date,
						upto_date=posting_date,
						party_type=d.party_type,
						party=d.party,
					)
				)

			return current_rate_cache[cache_key]

		if account_details:
			# Accounts with balance in both Account and Base Currency.
			for d in [
				row
				for row in account_details
				if not row.zero_balance
			]:
				# Fetch current_rate from Journal Entry Account.
				journal_current_rate = fetch_current_rate(d)
				#frappe.msgprint(str(journal_current_rate))

				# Keep the original calculation as fallback.
				#frappe.msgprint(str(d))
				calculated_current_rate = (
					d.balance
					/ d.balance_in_account_currency
					if d.balance_in_account_currency
					else 0
				)
				#frappe.msgprint(str(cal))

				# current_exchange_rate = (
				# 	journal_current_rate
				# 	or calculated_current_rate
				# 	or 0.0
				# )
				current_exchange_rate = flt(
                d.get("current_rate") or 0.0
                 )

				# --------------------------------------------------
				# NEW EXCHANGE RATE: KEPT EXACTLY AS ORIGINAL
				# --------------------------------------------------
				# new_exchange_rate = get_exchange_rate(
				# 	d.account_currency,
				# 	"USD",
				# 	posting_date,
				# )
				#frappe.throw(str(journal_current_rate))
				# new_rate = frappe.db.get_value(
				# 			"Currency Exchange",
				# 			{
				# 				"from_currency": "BTN",
				# 				"to_currency": "USD",
				# 				"date": posting_date,
				# 			},
				# 			"exchange_rate"
				# 		)
				# new_exchange_rate=new_rate or 1
				#frappe.throw(str(new_exchange_rate))
				currency_exchange = frappe.db.get_value(
					"Currency Exchange",
					{
						"from_currency": company_currency,
						"date": posting_date,
					},
					[
						"from_currency",
						"to_currency",
						"exchange_rate",
					],
					as_dict=True,
				)
				#frappe.throw(str(posting_date))
				new_exchange=frappe.db.sql(f""" select exchange_rate from `tabCurrency Exchange` where date=%s and from_currency='BTN' and to_currency='USD' limit 1""",posting_date,as_dict=1)
				#0frappe.throw(str(new_exchange))
				if new_exchange and new_exchange[0].get('exchange_rate'):
					new_exchange_rate = flt(new_exchange[0].exchange_rate)
				else:
					new_exchange_rate = 0.0

				new_balance_in_base_currency = flt(
					d.balance_in_account_currency
					/ new_exchange_rate
				)

				gain_loss = flt(
					new_balance_in_base_currency,
					precision,
				) - flt(
					d.balance,
					precision,
				)

				accounts.append(
					{
						"account": d.account,
						"party_type": d.party_type,
						"party": d.party,
						"account_currency": (
							d.account_currency
						),
						"balance_in_base_currency": (
							d.balance
						),
						"balance_in_account_currency": (
							d.balance_in_account_currency
						),
						"zero_balance": (
							d.zero_balance
						),
						"current_exchange_rate": (
							current_exchange_rate
						),
						"new_exchange_rate": (
							new_exchange_rate
						),
						"new_balance_in_base_currency": (
							new_balance_in_base_currency
						),
						"new_balance_in_account_currency": (
							d.balance_in_account_currency
						),
						"gain_loss": gainloss_btn,
					}
				)

			# Accounts with zero balance in either Account or Base Currency.
			for d in [
				row
				for row in account_details
				if row.zero_balance
			]:
				journal_current_rate = fetch_current_rate(d)
				#frappe.msgprint(str(d))
				if d.balance != 0:
					current_exchange_rate = (
						journal_current_rate
						or 0.0
					)

					# Keep original zero-balance logic.
					new_exchange_rate = 0
					new_balance_in_account_currency = 0
					new_balance_in_base_currency = 0

					gain_loss = flt(
						new_balance_in_base_currency,
						precision,
					) - flt(
						d.balance,
						precision,
					)

				else:
					# Keep original zero-balance logic.
					new_exchange_rate = 0
					new_balance_in_base_currency = 0
					new_balance_in_account_currency = 0

					current_exchange_rate = (
						journal_current_rate
						or calculate_exchange_rate_using_last_gle(
							company,
							d.account,
							d.party_type,
							d.party,
						)
						or 0.0
					)

					gain_loss = (
						new_balance_in_account_currency
						- (
							current_exchange_rate
							* d.balance_in_account_currency
						)
					)

				accounts.append(
					{
						"account": d.account,
						"party_type": d.party_type,
						"party": d.party,
						"account_currency": (
							d.account_currency
						),
						"balance_in_base_currency": (
							d.balance
						),
						"balance_in_account_currency": (
							d.balance_in_account_currency
						),
						"zero_balance": (
							d.zero_balance
						),
						"current_exchange_rate": (
							current_exchange_rate
						),
						"new_exchange_rate": (
							new_exchange_rate
						),
						"new_balance_in_base_currency": (
							new_balance_in_base_currency
						),
						"new_balance_in_account_currency": (
							new_balance_in_account_currency
						),
						"gain_loss": gain_loss,
					}
				)

		return accounts

	def throw_invalid_response_message(
		self,
		account_details,
	):
		if account_details:
			message = _(
				"No outstanding invoices require exchange rate revaluation"
			)
		else:
			message = _(
				"No outstanding invoices found"
			)

		frappe.msgprint(message)

	def get_for_unrealized_gain_loss_account(self):
		
		unrealized_exchange_gain_loss_account = (
			frappe.get_cached_value(
				"Company",
				self.company,
				"unrealized_exchange_gain_loss_account",
			)
		)
		
		if not unrealized_exchange_gain_loss_account:
			frappe.throw(
				_(
					"Please set Unrealized Exchange Gain/Loss "
					"Account in Company {0}"
				).format(self.company)
			)

		return unrealized_exchange_gain_loss_account

	# @frappe.whitelist()
	# def make_jv_entries(self):
		
	# 	zero_balance_jv = (
	# 		self.make_jv_for_zero_balance()
	# 	)

	# 	if zero_balance_jv:
	# 		frappe.msgprint(
	# 			f"Zero Balance Journal: "
	# 			f"{get_link_to_form('Journal Entry', zero_balance_jv.name)}"
	# 		)

	# 	revaluation_jv = (
	# 		self.make_jv_for_revaluation()
	# 	)

	# 	if revaluation_jv:
	# 		frappe.msgprint(
	# 			f"Revaluation Journal: "
	# 			f"{get_link_to_form('Journal Entry', revaluation_jv.name)}"
	# 		)

	# 	return {
	# 		"revaluation_jv": (
	# 			revaluation_jv.name
	# 			if revaluation_jv
	# 			else None
	# 		),
	# 		"zero_balance_jv": (
	# 			zero_balance_jv.name
	# 			if zero_balance_jv
	# 			else None
	# 		),
	# 	}

	# def make_jv_for_zero_balance(self):
		
	# 	if self.gain_loss_booked == 0:
	# 		return

	# 	accounts = [
	# 		row
	# 		for row in self.accounts
	# 		if row.zero_balance
	# 	]

	# 	if not accounts:
	# 		return

	# 	unrealized_exchange_gain_loss_account = (
	# 		self.get_for_unrealized_gain_loss_account()
	# 	)

	# 	journal_entry = frappe.new_doc(
	# 		"Journal Entry"
	# 	)

	# 	journal_entry.voucher_type = (
	# 		"Exchange Gain Or Loss"
	# 	)

	# 	journal_entry.company = self.company
	# 	journal_entry.posting_date = self.posting_date
	# 	journal_entry.multi_currency = 0

	# 	journal_entry_accounts = []

	# 	for d in accounts:
	# 		frappe.throw("kkk")
	# 		journal_account = frappe._dict(
	# 			{
	# 				"account": d.get("account"),
	# 				"party_type": d.get("party_type"),
	# 				"party": d.get("party"),
	# 				"account_currency": d.get(
	# 					"account_currency"
	# 				),
	# 				"balance": flt(
	# 					d.get(
	# 						"balance_in_account_currency"
	# 					),
	# 					d.precision(
	# 						"balance_in_account_currency"
	# 					),
	# 				),
	# 				"exchange_rate": 0,
	# 				"cost_center": (
	# 					erpnext.get_default_cost_center(
	# 						self.company
	# 					)
	# 				),
	# 				"reference_type": (
	# 					"Exchange Rate Revaluation"
	# 				),
	# 				"reference_name": self.name,
	# 			}
	# 		)

	# 	# 	if (
	# 	# 		d.get(
	# 	# 			"balance_in_account_currency"
	# 	# 		)
	# 	# 		and not d.get(
	# 	# 			"new_balance_in_account_currency"
	# 	# 		)
	# 	# 	):
			
	# 	# 		dr_or_cr = (
	# 	# 			"credit_in_account_currency"
	# 	# 			if d.get(
	# 	# 				"balance_in_account_currency"
	# 	# 			) > 0
	# 	# 			else "debit_in_account_currency"
	# 	# 		)

	# 	# 		reverse_dr_or_cr = (
	# 	# 			"debit_in_account_currency"
	# 	# 			if dr_or_cr
	# 	# 			== "credit_in_account_currency"
	# 	# 			else "credit_in_account_currency"
	# 	# 		)

	# 	# 		journal_account.update(
	# 	# 			{
	# 	# 				dr_or_cr: flt(
	# 	# 					abs(
	# 	# 						d.get(
	# 	# 							"balance_in_account_currency"
	# 	# 						)
	# 	# 					),
	# 	# 					d.precision(
	# 	# 						"balance_in_account_currency"
	# 	# 					),
	# 	# 				),
	# 	# 				reverse_dr_or_cr: 0,
	# 	# 				"debit": 0,
	# 	# 				"credit": 0,
	# 	# 			}
	# 	# 		)

	# 	# 		journal_entry_accounts.append(
	# 	# 			journal_account
	# 	# 		)

	# 	# 		journal_entry_accounts.append(
	# 	# 			{
	# 	# 				"account": (
	# 	# 					unrealized_exchange_gain_loss_account
	# 	# 				),
	# 	# 				"balance": get_balance_on(
	# 	# 					unrealized_exchange_gain_loss_account
	# 	# 				),
	# 	# 				"debit": 0,
	# 	# 				"credit": 0,
	# 	# 				"debit_in_account_currency": (
	# 	# 					abs(d.gain_loss)
	# 	# 					if d.gain_loss < 0
	# 	# 					else 0
	# 	# 				),
	# 	# 				"credit_in_account_currency": (
	# 	# 					abs(d.gain_loss)
	# 	# 					if d.gain_loss > 0
	# 	# 					else 0
	# 	# 				),
	# 	# 				"cost_center": (
	# 	# 					erpnext.get_default_cost_center(
	# 	# 						self.company
	# 	# 					)
	# 	# 				),
	# 	# 				"exchange_rate": 1,
	# 	# 				"reference_type": (
	# 	# 					"Exchange Rate Revaluation"
	# 	# 				),
	# 	# 				"reference_name": self.name,
	# 	# 			}
	# 	# 		)

	# 	# 	elif (
	# 	# 		d.get(
	# 	# 			"balance_in_base_currency"
	# 	# 		)
	# 	# 		and not d.get(
	# 	# 			"new_balance_in_base_currency"
	# 	# 		)
	# 	# 	):
	# 	# 		frappe.throw("vvvvvvv")
	# 	# 		dr_or_cr = (
	# 	# 			"credit"
	# 	# 			if d.get(
	# 	# 				"balance_in_base_currency"
	# 	# 			) > 0
	# 	# 			else "debit"
	# 	# 		)

	# 	# 		reverse_dr_or_cr = (
	# 	# 			"debit"
	# 	# 			if dr_or_cr == "credit"
	# 	# 			else "credit"
	# 	# 		)

	# 	# 		journal_account.update(
	# 	# 			{
	# 	# 				dr_or_cr: flt(
	# 	# 					abs(
	# 	# 						d.get(
	# 	# 							"balance_in_base_currency"
	# 	# 						)
	# 	# 					),
	# 	# 					d.precision(
	# 	# 						"balance_in_base_currency"
	# 	# 					),
	# 	# 				),
	# 	# 				reverse_dr_or_cr: 0,
	# 	# 				"debit_in_account_currency": 0,
	# 	# 				"credit_in_account_currency": 0,
	# 	# 			}
	# 	# 		)

	# 	# 		journal_entry_accounts.append(
	# 	# 			journal_account
	# 	# 		)

	# 	# 		journal_entry_accounts.append(
	# 	# 			{
	# 	# 				"account": (
	# 	# 					unrealized_exchange_gain_loss_account
	# 	# 				),
	# 	# 				"balance": get_balance_on(
	# 	# 					unrealized_exchange_gain_loss_account
	# 	# 				),
	# 	# 				"debit": (
	# 	# 					abs(d.gain_loss)
	# 	# 					if d.gain_loss < 0
	# 	# 					else 0
	# 	# 				),
	# 	# 				"credit": (
	# 	# 					abs(d.gain_loss)
	# 	# 					if d.gain_loss > 0
	# 	# 					else 0
	# 	# 				),
	# 	# 				"debit_in_account_currency": 0,
	# 	# 				"credit_in_account_currency": 0,
	# 	# 				"cost_center": (
	# 	# 					erpnext.get_default_cost_center(
	# 	# 						self.company
	# 	# 					)
	# 	# 				),
	# 	# 				"exchange_rate": 1,
	# 	# 				"reference_type": (
	# 	# 					"Forex Translation Revaluation"
	# 	# 				),
	# 	# 				"reference_name": self.name,
	# 	# 			}
	# 	# 		)

	# 	# journal_entry.set(
	# 	# 	"accounts",
	# 	# 	journal_entry_accounts,
	# 	# )

	# 	# journal_entry.set_total_debit_credit()
	# 	# journal_entry.save()

	# 	# return journal_entry

	# def make_jv_for_revaluation(self):
	
	# 	if self.gain_loss_unbooked == 0:
	# 		return

	# 	accounts = [
	# 		row
	# 		for row in self.accounts
	# 		if not row.zero_balance
	# 	]

	# 	if not accounts:
	# 		return

	# 	unrealized_exchange_gain_loss_account = (
	# 		self.get_for_unrealized_gain_loss_account()
	# 	)

	# 	journal_entry = frappe.new_doc(
	# 		"Journal Entry"
	# 	)

	# 	journal_entry.voucher_type = (
	# 		"Forex Translation Revaluation"
	# 	)

	# 	journal_entry.company = self.company
	# 	journal_entry.naming_series = "Journal Voucher"
	# 	journal_entry.branch = self.branch
	# 	journal_entry.posting_date = self.posting_date
	# 	journal_entry.multi_currency = 0

	# 	journal_entry_accounts = []

	# 	for d in accounts:
	# 		if not flt(
	# 			d.get(
	# 				"balance_in_account_currency"
	# 			),
	# 			d.precision(
	# 				"balance_in_account_currency"
	# 			),
	# 		):
	# 			continue

	# 		dr_or_cr = (
	# 			"debit_in_account_currency"
	# 			if d.get(
	# 				"balance_in_account_currency"
	# 			) > 0
	# 			else "credit_in_account_currency"
	# 		)

	# 		reverse_dr_or_cr = (
	# 			"debit_in_account_currency"
	# 			if dr_or_cr
	# 			== "credit_in_account_currency"
	# 			else "credit_in_account_currency"
	# 		)

	# 		journal_entry_accounts.append(
	# 			{
	# 				"account": d.get("account"),
	# 				"party_type": d.get("party_type"),
	# 				"party": d.get("party"),
	# 				"account_currency": d.get(
	# 					"account_currency"
	# 				),
	# 				"balance": flt(
	# 					d.get(
	# 						"balance_in_account_currency"
	# 					),
	# 					d.precision(
	# 						"balance_in_account_currency"
	# 					),
	# 				),
	# 				dr_or_cr: flt(
	# 					abs(
	# 						d.get(
	# 							"balance_in_account_currency"
	# 						)
	# 					),
	# 					d.precision(
	# 						"balance_in_account_currency"
	# 					),
	# 				),
	# 				"cost_center": (
	# 					erpnext.get_default_cost_center(
	# 						self.company
	# 					)
	# 				),
	# 				"exchange_rate": flt(
	# 					d.get(
	# 						"new_exchange_rate"
	# 					),
	# 					d.precision(
	# 						"new_exchange_rate"
	# 					),
	# 				),
	# 				"reference_type": (
	# 					"Forex Translation Revaluation"
	# 				),
	# 				"reference_name": self.name,
	# 			}
	# 		)

	# 		journal_entry_accounts.append(
	# 			{
	# 				"account": d.get("account"),
	# 				"party_type": d.get("party_type"),
	# 				"party": d.get("party"),
	# 				"account_currency": d.get(
	# 					"account_currency"
	# 				),
	# 				"balance": flt(
	# 					d.get(
	# 						"balance_in_account_currency"
	# 					),
	# 					d.precision(
	# 						"balance_in_account_currency"
	# 					),
	# 				),
	# 				reverse_dr_or_cr: flt(
	# 					abs(
	# 						d.get(
	# 							"balance_in_account_currency"
	# 						)
	# 					),
	# 					d.precision(
	# 						"balance_in_account_currency"
	# 					),
	# 				),
	# 				"cost_center": (
	# 					erpnext.get_default_cost_center(
	# 						self.company
	# 					)
	# 				),
	# 				"exchange_rate": flt(
	# 					d.get(
	# 						"current_exchange_rate"
	# 					),
	# 					d.precision(
	# 						"current_exchange_rate"
	# 					),
	# 				),
	# 				"reference_type": (
	# 					"Forex Translation Revaluation"
	# 				),
	# 				"reference_name": self.name,
	# 			}
	# 		)

	# 	journal_entry.set(
	# 		"accounts",
	# 		journal_entry_accounts,
	# 	)

	# 	journal_entry.set_amounts_in_company_currency()
	# 	journal_entry.set_total_debit_credit()

	# 	self.gain_loss_unbooked += (
	# 		journal_entry.difference
	# 		- self.gain_loss_unbooked
	# 	)

	# 	journal_entry.append(
	# 		"accounts",
	# 		{
	# 			"account": (
	# 				unrealized_exchange_gain_loss_account
	# 			),
	# 			"balance": get_balance_on(
	# 				unrealized_exchange_gain_loss_account
	# 			),
	# 			"debit_in_account_currency": (
	# 				abs(self.gain_loss_unbooked)
	# 				if self.gain_loss_unbooked < 0
	# 				else 0
	# 			),
	# 			"credit_in_account_currency": (
	# 				self.gain_loss_unbooked
	# 				if self.gain_loss_unbooked > 0
	# 				else 0
	# 			),
	# 			"cost_center": (
	# 				erpnext.get_default_cost_center(
	# 					self.company
	# 				)
	# 			),
	# 			"exchange_rate": 1,
	# 			"reference_type": (
	# 				"Forex Translation Revaluation"
	# 			),
	# 			"reference_name": self.name,
	# 		},
	# 	)

	# 	journal_entry.set_amounts_in_company_currency()
	# 	journal_entry.set_total_debit_credit()
	# 	journal_entry.save()

	# 	return journal_entry

	@frappe.whitelist()
	def make_jv_entries(self):
		
		zero_balance_jv = (
			self.make_jv_for_zero_balance()
		)

		if zero_balance_jv:
			frappe.msgprint(
				f"Zero Balance Journal: "
				f"{get_link_to_form('Journal Entry', zero_balance_jv.name)}"
			)

		revaluation_jv = (
			self.make_jv_for_revaluation()
		)

		if revaluation_jv:
			frappe.msgprint(
				f"Revaluation Journal: "
				f"{get_link_to_form('Journal Entry', revaluation_jv.name)}"
			)

		return {
			"revaluation_jv": (
				revaluation_jv.name
				if revaluation_jv
				else None
			),
			"zero_balance_jv": (
				zero_balance_jv.name
				if zero_balance_jv
				else None
			),
		}

	def make_jv_for_zero_balance(self):
		
		if self.gain_loss_booked == 0:
			return

		accounts = [
			row
			for row in self.accounts
			if row.zero_balance
		]

		if not accounts:
			return

		unrealized_exchange_gain_loss_account = (
			self.get_for_unrealized_gain_loss_account()
		)

		journal_entry = frappe.new_doc(
			"Journal Entry"
		)

		journal_entry.voucher_type = (
			"Exchange Gain Or Loss"
		)

		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		journal_entry.multi_currency = 0

		journal_entry_accounts = []

		for d in accounts:
			# Get the balance to be zeroed
			balance = flt(
				d.get("gainloss_btn"),
				d.precision("gainloss_btn")
			)
			frappe.throw(str(balance))
			if balance == 0:
				continue

			# Determine if balance is debit or credit
			is_debit = balance > 0

			# Create entry to zero out the balance
			if is_debit:
				# If debit balance, credit to remove it
				journal_entry_accounts.append({
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"credit_in_account_currency": abs(balance),
					"debit_in_account_currency": 0,
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": flt(
						d.get("current_exchange_rate"),
						d.precision("current_exchange_rate")
					),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
				})
			else:
				# If credit balance, debit to remove it
				journal_entry_accounts.append({
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"debit_in_account_currency": abs(balance),
					"credit_in_account_currency": 0,
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": flt(
						d.get("current_exchange_rate"),
						d.precision("current_exchange_rate")
					),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
				})

			# Add corresponding gain/loss entry for this account
			gain_loss = flt(
				d.get("gainloss_btn"),
				d.precision("gainloss_btn")
			)

			if gain_loss != 0:
				frappe.throw("jjj77")
				journal_entry_accounts.append({
					"account": unrealized_exchange_gain_loss_account,
					"balance": get_balance_on(unrealized_exchange_gain_loss_account),
					"debit_in_account_currency": (
						abs(gain_loss) if gain_loss < 0 else 0
					),
					"credit_in_account_currency": (
						abs(gain_loss) if gain_loss > 0 else 0
					),
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": 1,
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
				})

		journal_entry.set(
			"accounts",
			journal_entry_accounts,
		)

		journal_entry.set_amounts_in_company_currency()
		journal_entry.set_total_debit_credit()
		journal_entry.save()

		return journal_entry

	def make_jv_for_revaluation(self):
		
		if self.gain_loss_unbooked == 0:
			return

		accounts = [
			row
			for row in self.accounts
			if not row.zero_balance
		]

		if not accounts:
			return

		unrealized_exchange_gain_loss_account = (
			self.get_for_unrealized_gain_loss_account()
		)

		journal_entry = frappe.new_doc(
			"Journal Entry"
		)

		journal_entry.voucher_type = (
			"Forex Translation Revaluation"
		)

		journal_entry.company = self.company
		journal_entry.naming_series = "Journal Voucher"
		journal_entry.branch = self.branch
		journal_entry.posting_date = self.posting_date
		journal_entry.multi_currency = 0

		journal_entry_accounts = []

		for d in accounts:
			# Get the new balance in account currency
			new_balance = flt(
				d.get("gainloss_btn"),
				d.precision("gainloss_btn")
			)
			
			if new_balance == 0:
				continue

			# Determine if the new balance is debit or credit
			is_debit = new_balance > 0
			#frappe.throw(str(d.get("account")))
			acc_type=frappe.get_doc("Account",d.get("account"))
			

			# Create single entry with new balance at new exchange rate
			if acc_type.root_type=="Asset":
				journal_entry_accounts.append({
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"debit_in_account_currency": abs(new_balance),
					"credit_in_account_currency": 0,
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": flt(
						d.get("new_exchange_rate"),
						d.precision("new_exchange_rate")
					),
					"reference_type": "Forex Translation Revaluation",
					"reference_name": self.name,
				})
			else:
				journal_entry_accounts.append({
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"credit_in_account_currency": abs(new_balance),
					"debit_in_account_currency": 0,
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": flt(
						d.get("new_exchange_rate"),
						d.precision("new_exchange_rate")
					),
					"reference_type": "Forex Translation Revaluation",
					"reference_name": self.name,
				})

		# Add the gain/loss entry to balance the journal
		total_debit = sum(
			row.get("debit_in_account_currency", 0) 
			for row in journal_entry_accounts
		)
		total_credit = sum(
			row.get("credit_in_account_currency", 0) 
			for row in journal_entry_accounts
		)
		
		# The difference should equal gain_loss_unbooked
		difference = total_debit - total_credit
		
		if difference != 0:
			journal_entry_accounts.append({
				"account": unrealized_exchange_gain_loss_account,
				"balance": get_balance_on(unrealized_exchange_gain_loss_account),
				"debit_in_account_currency": (
					abs(difference) if difference > 0 else 0
				),
				"credit_in_account_currency": (
					abs(difference) if difference < 0 else 0
				),
				"cost_center": erpnext.get_default_cost_center(self.company),
				"exchange_rate": 1,
				"reference_type": "Forex Translation Revaluation",
				"reference_name": self.name,
			})

		journal_entry.set(
			"accounts",
			journal_entry_accounts,
		)

		journal_entry.set_amounts_in_company_currency()
		journal_entry.set_total_debit_credit()
		journal_entry.save()

		return journal_entry


def get_current_rate_from_journal_entry(
	company,
	account,
	upto_date,
	party_type=None,
	party=None,
):
	"""
	Fetch current_rate from the latest submitted
	Journal Entry Account row.

	Current Rate field:
	    Parent DocType: Journal Entry
	    Child DocType: Journal Entry Account
	    Fieldname: current_rate
	"""
	
	if not (
		company
		and account
		and upto_date
	):
		return 0.0

	conditions = [
		"je.docstatus = 1",
		"jea.docstatus = 1",
		"je.company = %(company)s",
		# "je.posting_date <= %(upto_date)s",
		"je.posting_date = %(upto_date)s",
		"jea.account = %(account)s",
		"IFNULL(jea.current_rate, 0) > 0",
	]

	values = {
		"company": company,
		"account": account,
		"upto_date": upto_date,
	}

	# Exact party matching prevents fetching a rate
	# from an unrelated party row.
	if party_type:
		conditions.append(
			"IFNULL(jea.party_type, '') = %(party_type)s"
		)

		values["party_type"] = party_type

	else:
		conditions.append(
			"IFNULL(jea.party_type, '') = ''"
		)

	if party:
		conditions.append(
			"IFNULL(jea.party, '') = %(party)s"
		)

		values["party"] = party

	else:
		conditions.append(
			"IFNULL(jea.party, '') = ''"
		)

	result = frappe.db.sql(
		f"""
			SELECT
				jea.current_rate,
				je.name AS journal_entry,
				je.posting_date
			FROM `tabJournal Entry Account` jea
			INNER JOIN `tabJournal Entry` je
				ON je.name = jea.parent
			WHERE {" AND ".join(conditions)}
			ORDER BY
				je.posting_date DESC,
				je.modified DESC,
				jea.idx DESC
			LIMIT 1
		""",
		values=values,
		as_dict=True,
	)

	if result:
		return flt(
			result[0].current_rate
		)

	return 0.0


def calculate_exchange_rate_using_last_gle(
	company,
	account,
	party_type,
	party,
):
	"""
	Use the last GL Entry to calculate the exchange rate.

	This remains as a fallback when current_rate
	is not available in Journal Entry Account.
	"""

	last_exchange_rate = None

	if company and account:
		gl = qb.DocType("GL Entry")

		conditions = []

		conditions.append(
			gl.company == company
		)

		conditions.append(
			gl.account == account
		)

		conditions.append(
			gl.is_cancelled == 0
		)

		conditions.append(
			(gl.debit > 0)
			| (gl.credit > 0)
		)

		conditions.append(
			(gl.debit_in_account_currency > 0)
			| (gl.credit_in_account_currency > 0)
		)

		if party_type:
			conditions.append(
				gl.party_type == party_type
			)

		if party:
			conditions.append(
				gl.party == party
			)

		result = (
			qb.from_(gl)
			.select(
				gl.voucher_type,
				gl.voucher_no,
			)
			.where(
				Criterion.all(conditions)
			)
			.orderby(
				gl.posting_date,
				order=Order.desc,
			)
			.limit(1)
			.run()
		)

		if result:
			voucher_type = result[0][0]
			voucher_no = result[0][1]

			rate_result = (
				qb.from_(gl)
				.select(
					(
						gl.debit
						- gl.credit
					)
					/
					(
						gl.debit_in_account_currency
						- gl.credit_in_account_currency
					)
				)
				.where(
					(gl.voucher_type == voucher_type)
					& (gl.voucher_no == voucher_no)
					& (gl.account == account)
				)
				.orderby(
					gl.posting_date,
					order=Order.desc,
				)
				.limit(1)
				.run()
			)

			if (
				rate_result
				and rate_result[0][0]
			):
				last_exchange_rate = (
					rate_result[0][0]
				)

	return last_exchange_rate or 0.0


@frappe.whitelist()
def get_account_details(
	company,
	posting_date,
	account,
	party_type=None,
	party=None,
	rounding_loss_allowance: float | None = None,
	from_date=None,
	to_date=None,
):
	if not (
		company
		and posting_date
	):
		frappe.throw(
			_("Company and Posting Date is mandatory")
		)

	account_currency, account_type = (
		frappe.get_cached_value(
			"Account",
			account,
			[
				"account_currency",
				"account_type",
			],
		)
	)

	if (
		account_type in [
			"Receivable",
			"Payable",
		]
		and not (
			party_type
			and party
		)
	):
		frappe.throw(
			_(
				"Party Type and Party is mandatory "
				"for {0} account"
			).format(account_type)
		)

	account_details = {
		"account_currency": account_currency,
	}

	from_date = (
		from_date
		or "1900-01-01"
	)

	to_date = (
		to_date
		or posting_date
	)

	account_balance = (
		ForexTranslationRevaluation.get_account_balance_from_gle(
			company=company,
			posting_date=posting_date,
			from_date=from_date,
			to_date=to_date,
			account=account,
			party_type=party_type,
			party=party,
			rounding_loss_allowance=(
				rounding_loss_allowance or 0
			),
		)
	)

	matching_account_balance = next(
		(
			row
			for row in account_balance
			if row.account == account
			and (
				row.party_type or ""
			) == (
				party_type or ""
			)
			and (
				row.party or ""
			) == (
				party or ""
			)
		),
		account_balance[0]
		if account_balance
		else None,
	)

	if (
		matching_account_balance
		and (
			matching_account_balance.balance
			or matching_account_balance.balance_in_account_currency
		)
	):
		account_with_new_balance = (
			ForexTranslationRevaluation.calculate_new_account_balance(
				company=company,
				posting_date=posting_date,
				account_details=[
					matching_account_balance
				],
				rate_upto_date=to_date,
			)
		)

		if account_with_new_balance:
			row = account_with_new_balance[0]

			account_details.update(
				{
					"balance_in_base_currency": (
						row[
							"balance_in_base_currency"
						]
					),
					"balance_in_account_currency": (
						row[
							"balance_in_account_currency"
						]
					),
					"current_exchange_rate": (
						row[
							"current_exchange_rate"
						]
					),
					"new_exchange_rate": (
						row[
							"new_exchange_rate"
						]
					),
					"new_balance_in_base_currency": (
						row[
							"new_balance_in_base_currency"
						]
					),
					"new_balance_in_account_currency": (
						row[
							"new_balance_in_account_currency"
						]
					),
					"zero_balance": (
						row[
							"zero_balance"
						]
					),
					"gain_loss": (
						row[
							"gain_loss"
						]
					),
				}
			)

	return account_details