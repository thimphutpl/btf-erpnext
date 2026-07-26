# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import datetime
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_months, flt, fmt_money, get_last_day, getdate, get_first_day
from frappe.model.mapper import get_mapped_doc
import json

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)
from erpnext.accounts.utils import get_fiscal_year


class BudgetError(frappe.ValidationError):
    pass

class DuplicateBudgetError(frappe.ValidationError):
    pass


class BudgetProposal(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.budget.doctype.budget_accounts.budget_accounts import BudgetAccounts
        from erpnext.budget.doctype.budget_activities.budget_activities import BudgetActivities
        from erpnext.budget.doctype.budget_cost_center.budget_cost_center import BudgetCostCenter
        from erpnext.budget.doctype.budget_proposal_account.budget_proposal_account import BudgetProposalAccount
        from erpnext.budget.doctype.budget_sub_activities.budget_sub_activities import BudgetSubActivities
        from erpnext.budget.doctype.source_of_funds.source_of_funds import SourceofFunds
        from frappe.types import DF

        accounts: DF.Table[BudgetProposalAccount]
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
        budget_accounts: DF.TableMultiSelect[BudgetAccounts]
        budget_activities: DF.TableMultiSelect[BudgetActivities]
        budget_against: DF.Literal["Cost Center"]
        budget_sub_activities: DF.TableMultiSelect[BudgetSubActivities]
        budget_type: DF.Data | None
        company: DF.Link
        cost_center: DF.Link
        cost_centers: DF.TableMultiSelect[BudgetCostCenter]
        deviation: DF.Percent
        fiscal_year: DF.Link
        initial_budget: DF.Currency
        monthly_distribution: DF.Link | None
        posting_date: DF.Date
        project: DF.Link | None
        project_name: DF.Data | None
        source_of_funds: DF.TableMultiSelect[SourceofFunds]
        supp_total: DF.Currency
        withdrawal_budget: DF.Currency
    # end: auto-generated types

    
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.budget.doctype.budget_account.budget_account import BudgetAccount
        from erpnext.budget.doctype.budget_accounts.budget_accounts import BudgetAccounts
        from erpnext.budget.doctype.budget_activities.budget_activities import BudgetActivities
        from erpnext.budget.doctype.budget_cost_center.budget_cost_center import BudgetCostCenter
        from erpnext.budget.doctype.budget_sub_activities.budget_sub_activities import BudgetSubActivities
        from erpnext.budget.doctype.source_of_funds.source_of_funds import SourceofFunds
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
        branch: DF.Link | None
        budget_accounts: DF.TableMultiSelect[BudgetAccounts]
        budget_activities: DF.TableMultiSelect[BudgetActivities]
        budget_against: DF.Literal["", "Cost Center", "Project"]
        budget_sub_activities: DF.TableMultiSelect[BudgetSubActivities]
        budget_type: DF.Data | None
        company: DF.Link
        cost_center: DF.Link
        cost_centers: DF.TableMultiSelect[BudgetCostCenter]
        deviation: DF.Percent
        fiscal_year: DF.Link
        initial_budget: DF.Currency
        initial_total: DF.Currency
        monthly_distribution: DF.Link | None
        project: DF.Link | None
        project_name: DF.Data | None
        source_of_funds: DF.TableMultiSelect[SourceofFunds]
        supp_total: DF.Currency
        withdraw_budget: DF.Currency

    def autoname(self):
        self.name = make_autoname(
            "BUD" + "/" + self.fiscal_year + "/.###"
        )

    def validate(self):
        if not self.get(frappe.scrub(self.budget_against)):
            frappe.msgprint(_("{0} is mandatory").format(self.budget_against), raise_exception=True)
        self.validate_duplicate()
        self.validate_accounts()
        self.set_null_value()
        self.validate_applicable_for()
        self.calculate_budget()
        self.calculate_totals()
        self.budget_activities = []
        self.budget_sub_activities = []
        self.source_of_funds = []
        self.budget_accounts = []
        self.set_broad_head_from_account()
        # Generate combinations automatically
        # self.generate_combinations()

    def before_save(self):
        """Process duplicates before saving"""
        self.process_duplicate_names()
        # """Auto-generate combinations before saving"""
        # self.generate_combinations()

    def generate_combinations(self):
        """Generate combinations in hierarchical format"""
        
        # Only generate if we have selections
        if not (self.budget_activities or self.budget_sub_activities or self.source_of_funds or self.budget_accounts):
            return
        
        # Get selected values
        activities = [d.budget_activity for d in self.budget_activities] if self.budget_activities else []
        sources = [d.source_of_fund for d in self.source_of_funds] if self.source_of_funds else []
        accounts = [d.account for d in self.budget_accounts] if self.budget_accounts else []
        
        # Get sub-activities with their parent activity mapping
        sub_activities_by_activity = {}
        if self.budget_sub_activities:
            for bsa in self.budget_sub_activities:
                # Get the parent activity for this sub-activity
                parent_activity = frappe.db.get_value("Budget Sub Activity", bsa.budget_sub_activity, "budget_activity")
                if parent_activity not in sub_activities_by_activity:
                    sub_activities_by_activity[parent_activity] = []
                sub_activities_by_activity[parent_activity].append(bsa.budget_sub_activity)
        
        # Only generate if we have all required data
        if not activities or not sub_activities_by_activity or not sources or not accounts:
            return
        
        # Clear existing accounts
        self.set('accounts', [])
        
        # Generate combinations in hierarchical format
        for activity in activities:
            activity_doc = frappe.get_cached_doc("Budget Activity", activity)
            sub_activities = sub_activities_by_activity.get(activity, [])
            
            if not sub_activities:
                continue
            
            for sub_activity in sub_activities:
                sub_activity_doc = frappe.get_cached_doc("Budget Sub Activity", sub_activity)
                
                for source in sources:
                    source_doc = frappe.get_cached_doc("Source of Fund", source)
                    
                    for account_idx, account in enumerate(accounts):
                        account_doc = frappe.get_cached_doc("Account", account)
                        
                        row = self.append('accounts', {})
                        
                        # Set values - only for first account in each group
                        if account_idx == 0:
                            row.budget_activity = activity
                            row.budget_activity_name = activity_doc.activity_name
                            row.budget_sub_activity = sub_activity
                            row.budget_sub_activity_name = sub_activity_doc.sub_activity_name
                            row.source_of_fund = source
                            row.source_of_fund_name = source_doc.source_name
                        else:
                            # Leave empty for subsequent accounts
                            row.budget_activity = None
                            row.budget_activity_name = None
                            row.budget_sub_activity = None
                            row.budget_sub_activity_name = None
                            row.source_of_fund = None
                            row.source_of_fund_name = None
                        
                        # Always set account
                        row.account = account
                        row.account_name = account_doc.account_name
                        
                        # Initialize budget fields
                        # row.initial_budget = 0
                        # row.approved_budget = 0
                        row.initial_budget = ""
                        row.approved_budget = ""
                        row.supplementary_budget = 0
                        row.budget_received = 0
                        row.budget_sent = 0
                        row.budget_amount = 0	

    def process_duplicate_names(self):
        """Hide repeated values in hierarchical format"""

        prev_activity = None
        prev_sub_activity = None
        prev_source = None

        for row in self.accounts:

            current_activity = row.budget_activity
            current_sub_activity = row.budget_sub_activity
            current_source = row.source_of_fund

            # Always fetch account name
            if row.account:
                row.account_name = frappe.db.get_value(
                    "Account",
                    row.account,
                    "account_name"
                )

            # Activity
            if current_activity == prev_activity:
                row.budget_activity_name = ""
            else:
                row.budget_activity_name = current_activity
                prev_activity = current_activity

            # Sub Activity
            if (
                current_activity == prev_activity
                and current_sub_activity == prev_sub_activity
            ):
                row.budget_sub_activity_name = ""
            else:
                row.budget_sub_activity_name = current_sub_activity
                prev_sub_activity = current_sub_activity

            # Source
            if (
                current_activity == prev_activity
                and current_sub_activity == prev_sub_activity
                and current_source == prev_source
            ):
                row.source_of_fund_name = ""
            else:
                row.source_of_fund_name = current_source
                prev_source = current_source	

    def on_submit(self):
        """Create or update Budget document when Budget Proposal is submitted"""
        self.create_or_update_budget()
        # Validate approved_budget before submission
        self.validate_approved_budget()	

    def validate_approved_budget(self):
        """Validate that approved_budget is not empty/null for all rows"""
        missing_rows = []
        
        for idx, row in enumerate(self.accounts, 1):
            # Check if approved_budget is None, empty, or 0
            if not row.approved_budget or row.approved_budget == 0:
                # Track the row with relevant details
                row_info = {
                    'row_no': idx,
                    'account': row.account or 'N/A',
                    'account_name': row.account_name or 'N/A',
                    'cost_center': row.cost_center or 'N/A',
                    'budget_activity': row.budget_activity or 'N/A',
                    'budget_sub_activity': row.budget_sub_activity or 'N/A',
                    'source_of_fund': row.source_of_fund or 'N/A'
                }
                missing_rows.append(row_info)
        
        if missing_rows:
            # Build error message with table
            error_msg = _("Approved Budget is required for the following rows before submission:<br><br>")
            
            # Create HTML table for better readability
            table_html = """
            <table class="table table-bordered" style="width:100%;">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Account</th>
                        <th>Cost Center</th>
                        <th>Activity</th>
                        <th>Sub Activity</th>
                        <th>Source of Fund</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for row in missing_rows:
                table_html += f"""
                    <tr>
                        <td>{row['row_no']}</td>
                        <td><b>{row['account']}</b> - {row['account_name']}</td>
                        <td>{row['cost_center']}</td>
                        <td>{row['budget_activity']}</td>
                        <td>{row['budget_sub_activity']}</td>
                        <td>{row['source_of_fund']}</td>
                    </tr>
                """
            
            table_html += "</tbody></table>"
            
            error_msg += table_html
            
            # Throw error with details
            frappe.throw(error_msg, title=_("Approved Budget Missing"))				

    def on_update_after_submit(self):
        """Update Budget document when Budget Proposal is updated after submit"""
        self.create_or_update_budget()

    def on_cancel(self):
        """Cancel associated Budget document when Budget Proposal is cancelled"""
        self.cancel_budget()

    def set_broad_head_from_account(self):
        """Auto-set broad_head as parent_account of selected account"""
        for row in self.get("accounts"):  # Replace with your child table fieldname
            if row.account and not row.broad_head:
                parent_account = frappe.db.get_value("Account", row.account, "parent_account")
                if parent_account:
                    row.broad_head = parent_account
                else:
                    frappe.throw(f"Account {row.account} does not have a parent account")
            elif row.account and row.broad_head:
                # Optional: Validate that broad_head matches parent_account
                parent_account = frappe.db.get_value("Account", row.account, "parent_account")
                if parent_account and row.broad_head != parent_account:
                    frappe.throw(f"Broad Head {row.broad_head} does not match parent account {parent_account} of {row.account}")	

    def create_or_update_budget(self):
        """Create a new Budget document or update existing one"""
        # Check if Budget already exists for this proposal
        existing_budget = frappe.db.exists("Budget", {
            "budget_proposal": self.name,
            "docstatus": ["!=", 2]  # Not cancelled
        })
        
        if existing_budget:
            # Update existing budget
            budget_doc = frappe.get_doc("Budget", existing_budget[0])
            self.update_budget_doc(budget_doc)
            budget_doc.save()
        else:
            # Create new budget
            budget_doc = self.create_budget_doc()
            budget_doc.insert()
        
        # If budget is not submitted, submit it
        if budget_doc.docstatus == 0:
            budget_doc.submit()
        
        # Create clickable link
        budget_link = frappe.utils.get_link_to_form("Budget", budget_doc.name)
        frappe.msgprint(_("Budget {0} has been {1}").format(
            budget_link,
            "updated" if existing_budget else "created"
        ))

    def create_budget_doc(self):
        """Create a new Budget document from Budget Proposal"""
        budget = frappe.new_doc("Budget")
        self.map_proposal_to_budget(budget)
        budget.budget_proposal = self.name  # Link back to proposal
        return budget

    def update_budget_doc(self, budget):
        """Update existing Budget document from Budget Proposal"""
        self.map_proposal_to_budget(budget)
        budget.budget_proposal = self.name

    def map_proposal_to_budget(self, budget):
        """Map fields from Budget Proposal to Budget"""
        # Map basic fields
        budget.company = self.company
        budget.fiscal_year = self.fiscal_year
        budget.budget_against = self.budget_against
        budget.cost_center = self.cost_center
        budget.project = self.project
        budget.monthly_distribution = self.monthly_distribution
        
        # Map action fields
        budget.action_if_annual_budget_exceeded = self.action_if_annual_budget_exceeded
        budget.action_if_accumulated_monthly_budget_exceeded = self.action_if_accumulated_monthly_budget_exceeded
        budget.action_if_annual_budget_exceeded_on_mr = self.action_if_annual_budget_exceeded_on_mr
        budget.action_if_accumulated_monthly_budget_exceeded_on_mr = self.action_if_accumulated_monthly_budget_exceeded_on_mr
        budget.action_if_annual_budget_exceeded_on_po = self.action_if_annual_budget_exceeded_on_po
        budget.action_if_accumulated_monthly_budget_exceeded_on_po = self.action_if_accumulated_monthly_budget_exceeded_on_po
        
        # Map applicable flags
        budget.applicable_on_material_request = self.applicable_on_material_request
        budget.applicable_on_purchase_order = self.applicable_on_purchase_order
        budget.applicable_on_booking_actual_expenses = self.applicable_on_booking_actual_expenses
        
        # Clear existing accounts in budget
        budget.set('accounts', [])
        
        # Map accounts from proposal to budget
        for proposal_account in self.accounts:
            budget_account = budget.append('accounts', {})
            budget_account.account = proposal_account.account
            budget_account.broad_head = proposal_account.broad_head
            budget_account.cost_center = proposal_account.cost_center
            budget_account.budget_activity = proposal_account.budget_activity
            budget_account.budget_sub_activity = proposal_account.budget_sub_activity
            budget_account.source_of_fund = proposal_account.source_of_fund
            budget_account.initial_budget = proposal_account.initial_budget
            budget_account.approved_budget = proposal_account.approved_budget
            budget_account.supplementary_budget = proposal_account.supplementary_budget
            budget_account.budget_received = proposal_account.budget_received
            budget_account.budget_sent = proposal_account.budget_sent
            budget_account.budget_amount = proposal_account.approved_budget
            
            # Map monthly distribution if applicable
            if self.monthly_distribution:
                budget_account.january = proposal_account.january
                budget_account.february = proposal_account.february
                budget_account.march = proposal_account.march
                budget_account.april = proposal_account.april
                budget_account.may = proposal_account.may
                budget_account.june = proposal_account.june
                budget_account.july = proposal_account.july
                budget_account.august = proposal_account.august
                budget_account.september = proposal_account.september
                budget_account.october = proposal_account.october
                budget_account.november = proposal_account.november
                budget_account.december = proposal_account.december
        
        # Copy other table fields if they exist in Budget doctype
        if hasattr(budget, 'cost_centers') and self.cost_centers:
            budget.set('cost_centers', [])
            for cc in self.cost_centers:
                budget.append('cost_centers', {'cost_center': cc.cost_center})
        
        if hasattr(budget, 'budget_activities') and self.budget_activities:
            budget.set('budget_activities', [])
            for ba in self.budget_activities:
                budget.append('budget_activities', {'budget_activity': ba.budget_activity})
        
        if hasattr(budget, 'budget_sub_activities') and self.budget_sub_activities:
            budget.set('budget_sub_activities', [])
            for bsa in self.budget_sub_activities:
                budget.append('budget_sub_activities', {'budget_sub_activity': bsa.budget_sub_activity})
        
        if hasattr(budget, 'source_of_funds') and self.source_of_funds:
            budget.set('source_of_funds', [])
            for sf in self.source_of_funds:
                budget.append('source_of_funds', {'source_of_fund': sf.source_of_fund})
        
        if hasattr(budget, 'budget_accounts') and self.budget_accounts:
            budget.set('budget_accounts', [])
            for ba in self.budget_accounts:
                budget.append('budget_accounts', {'account': ba.account})

    def cancel_budget(self):
        """Cancel the associated Budget document"""
        existing_budget = frappe.db.exists("Budget", {
            "budget_proposal": self.name,
            "docstatus": 1  # Submitted
        })
        
        if existing_budget:
            budget_doc = frappe.get_doc("Budget", existing_budget)
            budget_doc.cancel()
            frappe.msgprint(_("Budget {0} has been cancelled").format(budget_doc.name))	

    # def validate_duplicate(self):
    # 	budget_against_field = frappe.scrub(self.budget_against)
    # 	budget_against = self.get(budget_against_field)

    # 	accounts = [d.account for d in self.accounts] or []
    # 	existing_budget = frappe.db.sql(
    # 		"""
    # 		select
    # 			b.name, ba.account from `tabBudget` b, `tabBudget Account` ba
    # 		where
    # 			ba.parent = b.name and b.docstatus < 2 and b.company = %s and ba.%s=%s and
    # 			b.fiscal_year=%s and b.name != %s and ba.account in (%s)"""
    # 		% ("%s", budget_against_field, "%s", "%s", "%s", ",".join(["%s"] * len(accounts))),
    # 		(self.company, budget_against, self.fiscal_year, self.name) + tuple(accounts),
    # 		as_dict=1)
    # 	if existing_budget:
    # 		for d in existing_budget:
    # 			frappe.msgprint(
    # 				_(
    # 					"Another Budget record '{0}' already exists against {1} '{2}' and account '{3}' for fiscal year {4}"
    # 				).format(d.name, self.budget_against, budget_against, d.account, self.fiscal_year),raise_exception=True
    # 			)

    def validate_duplicate(self):
        budget_against_field = frappe.scrub(self.budget_against)
        budget_against = self.get(budget_against_field)

        accounts = [d.account for d in self.accounts] or []
        if not accounts:
            return

        # Build conditions
        conditions = [
            "b.docstatus < 2",
            "b.company = %s",
            f"ba.{budget_against_field} = %s",
            "b.fiscal_year = %s",
            "b.name != %s"
        ]
        params = [self.company, budget_against, self.fiscal_year, self.name]

        # Add account condition
        account_placeholders = ','.join(['%s'] * len(accounts))
        conditions.append(f"ba.account IN ({account_placeholders})")
        params.extend(accounts)

        # Add source_of_fund condition if present
        source_of_funds = [d.source_of_fund for d in self.accounts if d.source_of_fund]
        if source_of_funds:
            source_placeholders = ','.join(['%s'] * len(source_of_funds))
            conditions.append(f"ba.source_of_fund IN ({source_placeholders})")
            params.extend(source_of_funds)

        # Build and execute query
        query = f"""
            SELECT b.name, ba.account, ba.source_of_fund 
            FROM `tabBudget` b, `tabBudget Account` ba
            WHERE ba.parent = b.name 
                AND {' AND '.join(conditions)}
        """
        
        existing_budget = frappe.db.sql(query, tuple(params), as_dict=1)
        
        if existing_budget:
            for d in existing_budget:
                if d.get('source_of_fund'):
                    frappe.msgprint(
                        _(
                            "Another Budget record '{0}' already exists against {1} '{2}', "
                            "account '{3}', and source of fund '{4}' for fiscal year {5}"
                        ).format(d.name, self.budget_against, budget_against, d.account, d.source_of_fund, self.fiscal_year),
                        raise_exception=True
                    )
                else:
                    frappe.msgprint(
                        _(
                            "Another Budget record '{0}' already exists against {1} '{2}' "
                            "and account '{3}' for fiscal year {4}"
                        ).format(d.name, self.budget_against, budget_against, d.account, self.fiscal_year),
                        raise_exception=True
                    )

    @frappe.whitelist()
    def get_consolidated_data(self):
        per_activity = {}

        for account in self.accounts:
            activity = account.budget_sub_activity
            if not activity or str(activity).strip() == "":
                continue

            source = getattr(account, 'source_of_fund', 'Unknown')
            budget = account.initial_budget or 0 

            if activity not in per_activity:
                per_activity[activity] = {
                    "total_budget_per_activity": 0,
                    "sources": {}
                }

            per_activity[activity]["total_budget_per_activity"] += budget

            if source not in per_activity[activity]["sources"]:
                per_activity[activity]["sources"][source] = budget
            else:
                per_activity[activity]["sources"][source] += budget

        r_data = []
        for activity, values in per_activity.items():
            sources_str = ", ".join(
                [f"{src}: {amt}" for src, amt in values["sources"].items()]
            )

            r_data.append({
                "budget_sub_activity": activity,
                "initial_budget": values["total_budget_per_activity"],
                "source_of_fund_summary": sources_str
            })

        return r_data

    @frappe.whitelist()
    def get_filtered_budget_data(self):
        r_data = []
        total = 0
        cond = ""
        if self.cost_center:
            cond += "and ba.cost_center = '{}'".format(self.cost_center)
        if len(self.budget_activities) > 0:
            cond += "and ba.budget_activity in ({})".format(", ".join("'"+ba.budget_activity+"'" for ba in self.budget_activities))
        if len(self.budget_sub_activities) > 0:
            cond += "and ba.budget_sub_activity in ({})".format(", ".join("'"+bsa.budget_sub_activity+"'" for bsa in self.budget_sub_activities))
        if len(self.source_of_funds) > 0:
            cond += "and ba.source_of_fund in ({})".format(", ".join("'"+sf.source_of_fund+"'" for sf in self.source_of_funds))
        if len(self.budget_accounts) > 0:
            cond += "and ba.account in ({})".format(", ".join("'"+bac.account+"'" for bac in self.budget_accounts))
        data = frappe.db.sql("""
                select ba.cost_center, ba.budget_activity,
                       ba.budget_sub_activity, ba.source_of_fund, ba.account, ba.initial_budget
                       from `tabBudget Account` ba where ba.parent = '{}'
                       {}
            """.format(self.name, cond), as_dict = 1)
        for d in data:
            r_data.append({"cost_center": d.cost_center, "budget_activity": d.budget_activity, "budget_sub_activity": d.budget_sub_activity, "account": d.account, "initial_budget": d.initial_budget})
            total += flt(d.initial_budget)
        if total > 0:
            r_data.append({"cost_center": "Total", "budget_activity": "", "budget_sub_activity": "", "account": "", "initial_budget":total})
            
        return r_data
        

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

                # if d.account+" - "+d.cost_center+" - "+d.budget_activity+" - "+d.budget_sub_activity in account_list:
                # 	frappe.msgprint(_("Account {0} has been entered for object code {1}, activity code {2} and sub activity code {3} multiple times").format(d.account, d.cost_center, d.budget_activity, d.budget_sub_activity), raise_exception=True)
                # else:
                # 	account_list.append(d.account+" - "+d.cost_center+" - "+d.budget_activity+" - "+d.budget_sub_activity)

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
                acc.budget_amount = flt(acc.approved_budget) + flt(acc.supplementary_budget) + flt(acc.budget_received) - flt(acc.budget_sent)
                acc.db_set("budget_amount", acc.budget_amount)

    # def calculate_totals(self): 
    # 	total_initial = 0
    # 	proposal_budget = 0
    # 	approved_budget =0
    # 	total_actual = 0
    # 	total_supplementary = 0
    # 	if self.accounts:
    # 		for item in self.accounts:
    # 			total_initial += flt(item.initial_budget)
    # 			approved_budget += flt(item.approved_budget)
    # 			proposal_budget += flt(item.initial_budget)
    # 			total_actual += flt(item.budget_amount)
    # 			total_supplementary += flt(item.supplementary_budget)

    # 		self.initial_total = total_initial
    # 		self.initial_budget = proposal_budget
    # 		self.actual_total = total_actual
    # 		self.supp_total = total_supplementary
    def calculate_totals(self): 
        total_initial = 0
        proposal_budget = 0
        approved_budget = 0
        total_actual = 0
        total_supplementary = 0

        if self.accounts:
            for item in self.accounts:
                total_initial += flt(item.initial_budget)
                approved_budget += flt(item.approved_budget)
                proposal_budget += flt(item.initial_budget)
                total_actual += flt(item.budget_amount)
                total_supplementary += flt(item.supplementary_budget)

            self.initial_total = total_initial
            self.initial_budget = proposal_budget
            self.actual_total = total_actual
            self.supp_total = total_supplementary
            self.approved_budget = approved_budget 

    @frappe.whitelist()
    def get_accounts(self):
        condition = " and a.budget_type = '{}'".format(self.budget_type) if self.budget_type else ""
        entries = frappe.db.sql("""select parent_account, a.name as account, a.budget_type, account_number
                            from tabAccount a
                            where a.is_group = 0
                            and (a.freeze_account is null or a.freeze_account != 'Yes')
                            and (a.is_centralized_budget = 0 or (a.is_centralized_budget =1 and a.cost_center='{cost_center}'))
                            and NOT EXISTS( select 1
                                from `tabBudget` b 
                                inner join `tabBudget Account` i
                                on b.name = i.parent
                                where  b.docstatus != 2
                                and i.account = a.name
                                and b.cost_center = '{cost_center}'
                                and b.fiscal_year = '{fiscal_year}'
                                and b.name != '{name}'
                            )
                            and EXISTS(select 1 
                                                from `tabBudget Settings Account Types` s
                                                where s.parent = 'Budget Settings'
                                                and s.account_type = a.account_type)
                            {condition}
                        """.format(fiscal_year =self.fiscal_year, cost_center=self.cost_center, name=self.name, condition = condition), as_dict=True)
        self.set('accounts', [])
        p_account = ""
        for d in entries:
            d.initial_budget = 0
            if d.parent_account == p_account:
                d.parent_account = ""
            else:
                p_account = d.parent_account
            row = self.append('accounts', {})
            row.update(d)
    @frappe.whitelist()
    def get_budget_heads(self):
        if self.cost_center:
            self.accounts = [acc for acc in self.accounts if acc.account and acc.budget_sub_activity and acc.source_of_fund]

            for b in self.budget_activities:
                for c in self.budget_sub_activities:
                    for d in self.source_of_funds:
                        for e in self.budget_accounts:
                            # exists = frappe.db.sql("""
                            # 	SELECT ba.name 
                            # 	FROM `tabBudget Proposal Account` ba, `tabBudget Proposal` b 
                            # 	WHERE ba.parent = b.name
                            # 	AND b.fiscal_year = %s
                            # 	AND b.docstatus < 2
                            # 	AND ba.account = %s
                            # 	AND ba.budget_activity = %s
                            # 	AND ba.budget_sub_activity = %s
                            # 	AND ba.source_of_fund = %s
                            # 	AND ba.cost_center = %s
                            # """, (
                            # 	self.fiscal_year,
                            # 	e.account,
                            # 	b.budget_activity,
                            # 	c.budget_sub_activity,
                            # 	d.source_of_fund,
                            # 	self.cost_center
                            # ))

                            # if not exists:
                                # row = self.append("accounts", {})
                                # row.cost_center = self.cost_center
                                # row.budget_activity = b.budget_activity
                                # row.budget_sub_activity = c.budget_sub_activity
                                # row.source_of_fund = d.source_of_fund
                                # row.account = e.account
                                # row.initial_budget = 0

                            row = self.append("accounts", {})
                            row.cost_center = self.cost_center
                            row.budget_activity = b.budget_activity
                            row.budget_sub_activity = c.budget_sub_activity
                            row.source_of_fund = d.source_of_fund
                            row.account = e.account
                            row.initial_budget = 0	
            self.budget_activities = []
            self.budget_sub_activities = []
            self.source_of_funds = []
            self.budget_accounts = []
            self.accounts = [
                acc for acc in self.accounts
                if acc.account and acc.budget_sub_activity and acc.source_of_fund
            ]

    
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
                    budget_cost_center = cc_doc.budget_cost_center if cc_doc.use_budget_from_parent else args.cost_center
                condition = " and b.cost_center='{}'".format(budget_cost_center)
            # condition += f""" and ba.budget_activity="{args.budget_activity}" and ba.budget_sub_activity="{args.budget_sub_activity}" and ba.source_of_fund="{args.source_of_fund}" """
            args.is_tree = False
            if not args.project:
                args.committed_cost_center = args.cost_center
                args.cost_center = budget_cost_center
   
            budget_records = frappe.db.sql(
                """
                select
                    b.{budget_against_field} as budget_against, b.actual_total, b.actual_total budget_amount, b.monthly_distribution,
                    ifnull(b.applicable_on_material_request, 0) as for_material_request,
                    ifnull(applicable_on_purchase_order, 0) as for_purchase_order,
                    ifnull(applicable_on_booking_actual_expenses,0) as for_actual_expenses,
                    b.action_if_annual_budget_exceeded, b.action_if_accumulated_monthly_budget_exceeded,
                    b.action_if_annual_budget_exceeded_on_mr, b.action_if_accumulated_monthly_budget_exceeded_on_mr,
                    b.action_if_annual_budget_exceeded_on_po, b.action_if_accumulated_monthly_budget_exceeded_on_po
                from
                    `tabBudget Release` b
                where
                    b.fiscal_year="{fiscal_year}"
                    and b.docstatus=1
                    {condition}
            """.format(
                    condition=condition, budget_against_field=budget_against,
                fiscal_year=args.fiscal_year, account=args.account),
                as_dict=True
            )  # nosec
   
            # frappe.throw(str(budget_records))

            if budget_records:
                validate_budget_records(args, error, budget_records, throw_error)
            elif throw_error:
                # frappe.msgprint(_("Budget Release not available for <b>%s </b> in %s <b>%s</b> for Budget Sub Activity <b>%s</b> under Budget Activity <b>%s</b> for fiscal year and month <b>%s</b>, <b>%s</b>" % (
                # 				args.account, budget_against, frappe.db.escape(args.get(budget_against)),args.budget_sub_activity, args.budget_activity, args.fiscal_year, str(args.posting_date).split("-")[1]
                # 			)), raise_exception=True
                # 		)
                frappe.msgprint(_("Budget Release not available for <b>%s </b> in %s <b>%s</b> for fiscal year and month <b>%s</b>, <b>%s</b>" % (
                                args.account, budget_against, frappe.db.escape(args.get(budget_against)), args.fiscal_year, str(args.posting_date).split("-")[1]
                            )), raise_exception=True
                        )
            else:
                # error.append("Budget Release not available for <b>%s </b> in %s <b>%s</b> for Budget Sub Activity <b>%s</b> under Budget Activity <b>%s</b> for fiscal year and month <b>%s</b>, <b>%s</b>" % (
                # 				args.account, budget_against, frappe.db.escape(args.get(budget_against)), args.budget_sub_activity, args.budget_activity, args.fiscal_year, str(args.posting_date).split("-")[1]
                # 			))
                # return error[0]
                error.append("Budget Release not available for <b>%s </b> in %s <b>%s</b> for fiscal year and month <b>%s</b>, <b>%s</b>" % (
                                args.account, budget_against, frappe.db.escape(args.get(budget_against)), args.fiscal_year, str(args.posting_date).split("-")[1]
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


#work under this method for budget release changes Kinley
def compare_expense_with_budget(args, error, budget_amount, action_for, action, budget_against, amount=0, throw_error=None):
    # frappe.throw(str(args))
    actual_expense = amount or args.amount
    if args.project:
        condition = " and cb.project = '{}'".format(budget_against)
    else:
        condition = " and cb.company = {}".format(frappe.db.escape(budget_against))
    args.fiscal_year = args.fiscal_year if args.fiscal_year else str(args.posting_date)[0:4]
    # frappe.throw(str(args.posting_date))
    start_date = get_first_day(args.posting_date)
    end_date = get_last_day(args.posting_date)
    committed = frappe.db.sql("""select SUM(cb.amount) as total 
                                from `tabCommitted Budget` cb 
                                where 1 = 1
                                {condition} 
                                and cb.reference_date between '{start_date}' and '{end_date}'""".format(condition=condition, 
                            account=frappe.db.escape(args.account), company=args.company, start_date=start_date, 
                            end_date=end_date), as_dict=True)

    consumed = frappe.db.sql("""select SUM(cb.amount) as total 
                                from `tabConsumed Budget` cb 
                                where 1 = 1
                                {condition} 
                                and cb.reference_date between '{start_date}' and '{end_date}'""".format(condition=condition, 
                            account=frappe.db.escape(args.account), company=args.company, start_date=start_date, 
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

    if flt(total_expense_amount) > flt(budget_amount):
        # frappe.throw(str(budget_amount))
        diff = flt(total_expense_amount) - flt(budget_amount)
        currency = frappe.get_cached_value("Company", args.company, "default_currency")
        message = ''
        if args.doctype in ("Purchase Order", "Purchase Invoice"):
            message = f" until #Row. {args.idx} with Item Code #{args.item_code}."
        msg = _("Monthly Budget for Account {1} against {2} {3} for fiscal year {8} and month {9} is {4} and available budget is {5} Including (Supplementary Budget,Budget Received,Budget Sent). It exceed by {6}{7}").format(
            _(action_for),
            frappe.bold(args.account),
            args.budget_against_field,
            frappe.bold(budget_against),
            frappe.bold(fmt_money(budget_amount, currency=currency)),
            frappe.bold(fmt_money(available_budget, currency=currency)),
            frappe.bold(fmt_money(diff, currency=currency)),
            message,
            frappe.bold(args.fiscal_year),
            frappe.bold(str(args.posting_date).split("-")[1]),

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


@frappe.whitelist()
def make_budget_release(source_name, target_doc=None):
    month = json.loads(frappe.form_dict.get("args"))
    month = month.get("month")
    accounts = frappe.get_all(
        "Budget Proposal Account",
        filters={"parent": source_name},
        fields=["initial_budget"]
    )

    for acc in accounts:
        if not acc.initial_budget or float(acc.initial_budget) <= 0:
            frappe.throw(_("Approved Budget is missing. Cannot create Budget Release."))
    def set_missing_values(source, target):
        target.month = month
    doc = get_mapped_doc(
        "Budget Proposal",
        source_name,
        {
            "Budget Proposal": {
                "doctype": "Budget Release",
                "validation": {
                    "docstatus": ["=", 1],
                },
            },
            "Budget Proposal Account": {
                "doctype": "Budget Release Account",
            },
        },
        target_doc,
        set_missing_values,
    )

    return doc

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

def get_accumulated_monthly_budget(company, budget_account, transaction_date, amount, fiscal_year):
    mydate = datetime.fromisoformat(str(transaction_date))
    month = mydate.month
    if frappe.db.get_value("Account", budget_account, "ignore_budget_check"):
        return
    budget_against = frappe.db.get_single_value("Budget Settings","budget_against")
    cond = ""
    if budget_against == "Company":
        cond += ''' and b.budget_against = "{}" and b.company = "{}" '''.format(budget_against, company)
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
                and company="{company}"
            """.format(from_date=month_first_date, to_date=month_last_date,account = budget_account, month = month_name, company=company, fiscal_year=fiscal_year))[0][0],2)
        monthly_received = frappe.db.sql("""
                select sum(amount)
                from `tabReappropriation Details`
                where fiscal_year = "{fiscal_year}"
                and to_account="{account}"
                and to_company="{company}"
                and to_month = "{month}"
            """.format(from_date=month_first_date, to_date=month_last_date, month = month_name, account = budget_account, company=company, fiscal_year=fiscal_year))[0][0]
        monthly_sent = frappe.db.sql("""
                select sum(amount)
                from `tabReappropriation Details`
                where fiscal_year = "{fiscal_year}"
                and from_account="{account}"
                and from_company="{company}"
                and from_month = "{month}"
            """.format(from_date=month_first_date, to_date=month_last_date,month = month_name, account = budget_account, company=company, fiscal_year=fiscal_year))[0][0]
        adjustment = flt(supplement,2) + flt(monthly_received,2) - flt(monthly_sent,2)
    if adjustment:
        sum =flt(adjustment) + flt(monthly_amount)
        return sum
    else:
        return monthly_amount

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
                args.company, budget_account, transaction_date, args.amount, args.fiscal_year
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
def validate_expense_against_budget(args, throw_error=True):
    args = frappe._dict(args)
    if args.is_cancelled:
        delete_committed_consumed_budget(args.voucher_type, args.voucher_no)
        return
    error = []
    if args.get("company") and not args.fiscal_year:
        args.fiscal_year = get_fiscal_year(args.get("posting_date"), company=args.get("company"))[0]
        frappe.flags.exception_approver_role = frappe.get_cached_value(
            "Company", args.get("company"), "exception_budget_approver_role"
        )
        
    if not args.account:
        args.account = args.get("expense_account")

    if not args.get("account") and args.item_code:
        args.account = get_item_details(args)
    if not args.company:
        frappe.throw("Company is missing for budget check")

    if not args.account:
        frappe.msgprint("Budget Head/Account is missing. Please provide account to check budget", raise_exception=True)

    account_dtl = frappe.get_doc("Account", args.account)
    account_type = account_dtl.account_type
    if not account_type:
        frappe.throw("Account Type missing for Budget account <b>{}</b>".format(args.account))

    if account_dtl.ignore_budget_check:
        return

    budget_cost_center = None

    """ avoid budget check at MR """
    for budget_against in ["company", "cost_center"] + get_accounting_dimensions():
        if (
            args.get(budget_against)
            and args.account
            and frappe.db.get_value("Account", args.account, "account_type") in ["Expense Account","Fixed Asset"]
        ):
            doctype = frappe.unscrub(budget_against)
            args.budget_against_field = budget_against
            args.budget_against_doctype = doctype
            
            if budget_against == "company":
                condition = " and b.company = '{}'".format(args.company)
            else:
                if args.project:
                    condition = " and b.project = '{}'".format(args.project)
                    budget_cost_center = args.cost_center
                else:
                    bud_acc_dtl = frappe.get_doc("Account", args.account)
                    if bud_acc_dtl.is_centralized_budget:
                        budget_cost_center = bud_acc_dtl.cost_center
                    else:
                        cc_doc = frappe.get_doc("Cost Center", args.cost_center)
                        budget_cost_center = cc_doc.budget_cost_center if cc_doc.use_budget_from_parent else args.cost_center

                condition = " and b.cost_center='{}'".format(budget_cost_center)
            
            args.is_tree = False
            if not args.project:
                args.committed_cost_center = args.cost_center
                args.cost_center = budget_cost_center
            
            budget_records = frappe.db.sql(
                """
                select
                    b.{budget_against_field} as budget_against, b.actual_total, b.actual_total budget_amount, b.monthly_distribution,
                    ifnull(b.applicable_on_material_request, 0) as for_material_request,
                    ifnull(applicable_on_purchase_order, 0) as for_purchase_order,
                    ifnull(applicable_on_booking_actual_expenses,0) as for_actual_expenses,
                    b.action_if_annual_budget_exceeded, b.action_if_accumulated_monthly_budget_exceeded,
                    b.action_if_annual_budget_exceeded_on_mr, b.action_if_accumulated_monthly_budget_exceeded_on_mr,
                    b.action_if_annual_budget_exceeded_on_po, b.action_if_accumulated_monthly_budget_exceeded_on_po
                from
                    `tabBudget Release` b
                where
                    b.fiscal_year="{fiscal_year}"
                    and b.docstatus=1
                    {condition}
            """.format(
                    condition=condition, budget_against_field=budget_against,
                fiscal_year=args.fiscal_year, account=args.account),
                as_dict=True
            )

            if budget_records:
                validate_budget_records(args, error, budget_records, throw_error)
            else:
                error.append("Budget Release not available for <b>%s </b> in %s <b>%s</b> for fiscal year and month <b>%s</b>, <b>%s</b>" % (
                                args.account, budget_against, frappe.db.escape(args.get(budget_against)), args.fiscal_year, str(args.posting_date).split("-")[1]
                            ))
                return error[0]
            if len(error) > 0:
                return error[0]
                
    commit_budget(args)


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

@frappe.whitelist()
def get_parent_account(account):
    if not account:
        return ""
    parent = frappe.db.get_value("Account", account, "parent_account")
    return parent or ""		