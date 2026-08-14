// Copyright (c) 2016, Frappe Technologies and contributors
// For license information, please see license.txt111

frappe.ui.form.on("Party Type", {
	setup: function (frm) {
		frm.fields_dict["party_type"].get_query = function (frm) {
			return {
			
			};
		};
	},
});
