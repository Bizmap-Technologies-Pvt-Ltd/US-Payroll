// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.ui.form.on("Account Number", {
	refresh(frm) {
		frm.trigger("set_default_company");
	},

	onload: function (frm) {
		frm.trigger("set_default_company");
		frm.set_query("account_type", function (doc) {
			return {
				filters: {
					is_group: 1,
					company: doc.company,
				},
			};
		});
	},

	set_default_company: function (frm) {
		if (frm.doc.__islocal == 1) {
			frappe.call({
				method: "us_payroll.us_payroll.doctype.account_number.account_number.get_global_defaults_values",
				args: {
					doctype: "Global Defaults",
				},
				callback: function (r) {
					if (r.message) {
						let default_company = r.message.company;
						frm.set_value("company", default_company);
					}
				},
			});
		}
	},
});
