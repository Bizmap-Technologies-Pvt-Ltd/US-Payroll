frappe.ui.form.on("Journal Entry", {
	validate: function (frm) {},

	refresh: function (frm) {
		frm.trigger("set_posting_date");
		frm.trigger("set_default_company");
		frm.trigger("set_cheque_date");
	},

	onload: function (frm) {
		frm.trigger("set_posting_date");
		frm.trigger("set_default_company");
		frm.trigger("set_cheque_date");
	},

	set_default_company: function (frm) {
		if (frm.doc.__islocal == 1) {
			frappe.call({
				method: "us_payroll.custom_script.journal_entry.get_global_defaults_values",
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

	set_posting_date: function (frm) {
		const today = frappe.datetime.get_today();
		if (frm.doc.__islocal == 1) {
			frm.set_value("posting_date", today);
		}
	},

	set_cheque_date: function (frm) {
		const today = frappe.datetime.get_today();
		frm.set_value("cheque_date", today);
	},
});
