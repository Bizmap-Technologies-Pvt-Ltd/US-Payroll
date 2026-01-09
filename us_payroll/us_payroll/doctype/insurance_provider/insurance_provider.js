// Copyright (c) 2025, us_payroll and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insurance Provider", {

	setup: function (frm) {
		frm.set_query("account", "accounts", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: d.company,
				},
			};
		});
	},


	refresh(frm) {

	},
});
