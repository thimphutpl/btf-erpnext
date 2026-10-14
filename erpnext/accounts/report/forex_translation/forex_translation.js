// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Forex Translation"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"default": "2026-01-01",
			"reqd": 1
		},
		{
			"fieldname": "end_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": "2026-12-31",
			"reqd": 1
		},
		{
			"fieldname": "account",
			"label": __("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Account",
					"filters": {
						"company": company,
						"is_group": 0
					}
				}
			}
		},
		{
			"fieldname": "account_currency",
			"label": __("Account Currency"),
			"fieldtype": "Link",
			"options": "Currency"
		},
		{
			"fieldname": "include_opening_entries",
			"label": __("Include Opening Entries"),
			"fieldtype": "Check",
			"default": 1
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight the Adjustable Value column
		if (column.fieldname == "adjustable_value" && data) {
			if (data.adjustable_value > 0) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (data.adjustable_value < 0) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Highlight the Translation Difference column
		if (column.fieldname == "translation_difference" && data) {
			if (data.translation_difference > 0) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (data.translation_difference < 0) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	},

	"onload": function(report) {
		// Set default dates to 2026 if not set
		var filters = report.get_values();
		if (!filters || !filters.start_date) {
			report.set_filter_value('start_date', '2026-01-01');
			report.set_filter_value('end_date', '2026-12-31');
		}
	}
};