# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, add_to_date


def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data


def get_columns(filters):
    columns = [
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 250
        },
        {
            "label": _("Account Name"),
            "fieldname": "account_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _(f"Opening Balance ({filters.get('start_date')})"),
            "fieldname": "opening_balance",
            "fieldtype": "Currency",
            "options": "account_currency",
            "width": 150
        },
        {
            "label": _(f"Opening Rate ({filters.get('start_date')})"),
            "fieldname": "opening_rate",
            "fieldtype": "Float",
            "precision": 4,
            "width": 120
        },
        {
            "label": _(f"Closing Balance ({filters.get('end_date')})"),
            "fieldname": "closing_balance",
            "fieldtype": "Currency",
            "options": "account_currency",
            "width": 150
        },
        {
            "label": _(f"Closing Rate ({filters.get('end_date')})"),
            "fieldname": "closing_rate",
            "fieldtype": "Float",
            "precision": 4,
            "width": 120
        },
        {
            "label": _("Total Debit"),
            "fieldname": "total_debit",
            "fieldtype": "Currency",
            "options": "account_currency",
            "width": 130
        },
        {
            "label": _("Total Credit"),
            "fieldname": "total_credit",
            "fieldtype": "Currency",
            "options": "account_currency",
            "width": 130
        },
        {
            "label": _("Net Movement"),
            "fieldname": "net_movement",
            "fieldtype": "Currency",
            "options": "account_currency",
            "width": 130
        },
        {
            "label": _("Gain / Loss"),
            "fieldname": "gain_loss",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130
        },
    ]
    
    return columns


def get_data(filters):
    data = []
    
    # Get company currency
    company_currency = frappe.db.get_value("Company", filters.company, "default_currency")
    
    
    # Get all Bank accounts with account_currency = 'BTN'
    bank_accounts = get_bank_accounts(filters)
    
    if not bank_accounts:
        frappe.msgprint(_("No Bank accounts with BTN currency found for the selected company"))
        return data
    
    # Get all GL entries for these bank accounts with account_currency = 'BTN'
    account_list = [acc.name for acc in bank_accounts]
    gl_entries = get_btn_gl_entries(filters, account_list)
    
    # Calculate start year and end year dates
    start_date = getdate(filters.start_date)
    end_date = getdate(filters.end_date)
    
    # Get start of year for start_date (January 1st of start_date's year)
    start_year_start = getdate(f"{start_date.year}-01-01")
    # Get end of year for start_date (December 31st of start_date's year)
    start_year_end = getdate(f"{start_date.year}-12-31")
    
    # Get start of year for end_date
    end_year_start = getdate(f"{end_date.year}-01-01")
    # Get end of year for end_date
    end_year_end = getdate(f"{end_date.year}-12-31")
    
    # Group GL entries by account
    accounts_data = {}
    
    for entry in gl_entries:
        account = entry.account
        if account not in accounts_data:
            # Get account details
            account_doc = frappe.db.get_value("Account", account, 
                ["account_name", "account_currency"], as_dict=True)
            
            accounts_data[account] = {
                "account_name": account_doc.account_name if account_doc else "",
                "account_currency": account_doc.account_currency if account_doc else entry.account_currency,
                "entries": []
            }
        accounts_data[account]["entries"].append(entry)
    
    # Initialize totals
    total_net_movement_start_year = 0
    total_net_movement_end_year = 0
    total_gain_loss = 0
    
    for account, account_info in accounts_data.items():
        row = frappe._dict({
            "account": account,
            "account_name": account_info["account_name"],
            "account_currency": account_info["account_currency"]
        })
        
        # Get opening balance as of start date for this account
        opening_data = get_account_balance_btn(
            filters.company, 
            account, 
            filters.start_date, 
            "opening",
            filters.include_opening_entries
        )
        
        row.opening_balance = flt(opening_data.get("balance", 0))
        # Get opening rate from Currency Exchange based on date only
        row.opening_rate = get_exchange_rate(filters.start_date)
        
        # Get transactions between start and end date for this account
        period_data = get_account_balance_btn(
            filters.company, 
            account, 
            filters.start_date, 
            "period",
            filters.include_opening_entries,
            filters.end_date
        )
        
        row.total_debit = flt(period_data.get("debit", 0))
        row.total_credit = flt(period_data.get("credit", 0))
        row.net_movement = row.total_debit - row.total_credit
        
        # Calculate closing balance (opening + net movement)
        row.closing_balance = row.opening_balance + row.net_movement
        
        # Get closing rate from Currency Exchange based on date only
        row.closing_rate = get_exchange_rate(filters.end_date)
        
        # Calculate Gain/Loss: (Opening balance / opening_rate) - (Closing balance / closing_rate)
        # This gives the difference in base currency terms
        opening_base = row.opening_balance / row.opening_rate if row.opening_rate != 0 else 0
        closing_base = row.closing_balance / row.closing_rate if row.closing_rate != 0 else 0
        row.gain_loss = flt(closing_base - opening_base, 2)
        
        data.append(row)
        total_gain_loss += row.gain_loss
        
        # Calculate net movement for start year (all transactions in start_date's year)
        start_year_data = get_account_balance_btn(
            filters.company,
            account,
            start_year_start,
            "period",
            filters.include_opening_entries,
            start_year_end
        )
        start_year_net_movement = flt(start_year_data.get("debit", 0)) - flt(start_year_data.get("credit", 0))
        total_net_movement_start_year += start_year_net_movement
        
        # Calculate net movement for end year (all transactions in end_date's year)
        end_year_data = get_account_balance_btn(
            filters.company,
            account,
            end_year_start,
            "period",
            filters.include_opening_entries,
            end_year_end
        )
        end_year_net_movement = flt(end_year_data.get("debit", 0)) - flt(end_year_data.get("credit", 0))
        total_net_movement_end_year += end_year_net_movement
    
    # Add summary rows if there are accounts
    if data:
        # Add blank row for separation
        data.append(frappe._dict({
            "account": "",
            "account_name": "",
            "account_currency": "",
        }))
        
        # Add start year total row
        data.append(frappe._dict({
            "account": "Total Net Movement for Start year",
            "account_name": "",
            "account_currency": company_currency,
            "net_movement": total_net_movement_start_year
        }))
        
        # Add end year total row
        data.append(frappe._dict({
            "account": "Total Net Movement for End year",
            "account_name": "",
            "account_currency": company_currency,
            "net_movement": total_net_movement_end_year
        }))
        
        # Add adjustable value row (difference between end year and start year totals)
        adjustable_value = total_net_movement_end_year - total_net_movement_start_year
        data.append(frappe._dict({
            "account": "Adjustable Value",
            "account_name": "",
            "account_currency": company_currency,
            "net_movement": adjustable_value
        }))
        
        # Add total gain/loss row
        data.append(frappe._dict({
            "account": "Total Gain/Loss",
            "account_name": "",
            "account_currency": company_currency,
            "gain_loss": total_gain_loss
        }))
    
    return data


def get_bank_accounts(filters):
    """
    Get all Bank accounts with account_currency = 'BTN' for the company
    """
    conditions = ["a.company = %s", "a.account_type = 'Bank'", "a.is_group = 0", "a.account_currency = 'BTN'"]
    values = [filters.company]
    
    if filters.get("account"):
        conditions.append("a.name = %s")
        values.append(filters.account)
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT 
            a.name, 
            a.account_name, 
            a.account_currency
        FROM 
            `tabAccount` a
        WHERE 
            {where_clause}
        ORDER BY 
            a.name
    """
    
    return frappe.db.sql(query, tuple(values), as_dict=True)


def get_btn_gl_entries(filters, account_list=None):
    """
    Get all GL entries with account_currency = 'BTN' within the date range
    """
    conditions = ["gle.company = %s", "gle.account_currency = 'BTN'", "gle.is_cancelled = 0"]
    values = [filters.company]
    
    if account_list:
        conditions.append("gle.account IN %s")
        values.append(tuple(account_list))
    
    if filters.get("start_date") and filters.get("end_date"):
        conditions.append("gle.posting_date BETWEEN %s AND %s")
        values.extend([filters.start_date, filters.end_date])
    
    if filters.get("account") and not account_list:
        conditions.append("gle.account = %s")
        values.append(filters.account)
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT 
            gle.account,
            gle.account_currency,
            gle.posting_date,
            gle.debit_in_account_currency as debit,
            gle.credit_in_account_currency as credit,
            gle.debit as debit_in_base,
            gle.credit as credit_in_base,
            gle.voucher_type,
            gle.voucher_no,
            gle.against_voucher_type,
            gle.against_voucher,
            gle.remarks
        FROM 
            `tabGL Entry` gle
        WHERE 
            {where_clause}
        ORDER BY 
            gle.account, gle.posting_date, gle.creation
    """
    
    return frappe.db.sql(query, tuple(values), as_dict=True)


def get_account_balance_btn(company, account, date, balance_type, include_opening=False, end_date=None):
    """
    Get account balance as of a specific date or for a period
    balance_type: 'opening' or 'period'
    This function specifically filters for account_currency = 'BTN'
    """
    result = frappe._dict({
        "balance": 0,
        "debit": 0,
        "credit": 0,
        "exchange_rate": 1.0
    })
    
    conditions = ["gle.company = %s", "gle.account = %s", "gle.is_cancelled = 0", "gle.account_currency = 'BTN'"]
    values = [company, account]
    
    if balance_type == "opening":
        # Balance as of date (including date)
        conditions.append("gle.posting_date <= %s")
        values.append(date)
        
        if not include_opening:
            conditions.append("gle.is_opening = 'No'")
            
    elif balance_type == "period":
        # Transactions between start and end date
        # Use > for start_date to avoid double-counting with opening balance
        conditions.append("gle.posting_date > %s")
        conditions.append("gle.posting_date <= %s")
        values.extend([date, end_date])
        
        if not include_opening:
            conditions.append("gle.is_opening = 'No'")
    
    # Get balance and totals
    where_clause = " AND ".join(conditions)
    
    balance_query = f"""
        SELECT 
            SUM(gle.debit_in_account_currency) - SUM(gle.credit_in_account_currency) as balance,
            SUM(gle.debit_in_account_currency) as total_debit,
            SUM(gle.credit_in_account_currency) as total_credit
        FROM 
            `tabGL Entry` gle
        WHERE 
            {where_clause}
    """
    
    balance_result = frappe.db.sql(balance_query, tuple(values), as_dict=True)
    
    if balance_result and balance_result[0]:
        result.balance = flt(balance_result[0].balance)
        result.debit = flt(balance_result[0].total_debit)
        result.credit = flt(balance_result[0].total_credit)
    
    return result


def get_exchange_rate(date):
    """
    Get exchange rate from Currency Exchange doctype for a specific date
    Only uses date field to fetch the exchange_rate
    """
    # Convert date to string in proper format if it's a date object
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y-%m-%d')
    else:
        date_str = str(date)
    
    # Try to get the exchange rate for the exact date
    exact_match = frappe.db.sql("""
        SELECT name, exchange_rate, date 
        FROM `tabCurrency Exchange`
        WHERE date = %s
        ORDER BY creation DESC
        LIMIT 1
    """, date_str, as_dict=True)
    
    if exact_match:
        return flt(exact_match[0].exchange_rate)
    
    # If no exact match, get the most recent rate before or on the date
    recent_rate = frappe.db.sql("""
        SELECT exchange_rate, date 
        FROM `tabCurrency Exchange`
        WHERE date <= %s
        ORDER BY date DESC, creation DESC
        LIMIT 1
    """, date_str, as_dict=True)
    
    if recent_rate:
        return flt(recent_rate[0].exchange_rate)
    
    # If no rate found, return 1.0 as default
    return 1.0