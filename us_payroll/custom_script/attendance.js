frappe.ui.form.on("Attendance", {
	refresh: function (frm) {
		frm.trigger("set_default_company");
	},

	onload: function (frm) {
		frm.trigger("set_default_company");
	},

	validate: function (frm) {
		frm.trigger("set_default_company");
	},

	set_default_company: function (frm) {
		if (frm.doc.__islocal == 1) {
			frappe.call({
				method: "us_payroll.custom_script.attendance.get_global_defaults_values",
				args: {
					doctype: "Global Defaults",
				},
				callback: function (r) {
					if (r.message) {
						default_company = r.message.company;
						frm.set_value("company", default_company);
					}
				},
			});
		}
	},
});
