frappe.ui.form.on("Employee", {
	refresh: function (frm) {
		frm.set_df_property("holiday_list", "hidden", 0);
		frm.trigger("set_default_company");
		frm.trigger("filter_filing_method");
		frm.trigger("toggle_payroll_fields");
		frm.trigger("toggle_display_accrual_pto_rate");
	},

	onload: function (frm) {
		frm.trigger("set_default_company");
		frm.trigger("toggle_display_accrual_pto_rate");
		frm.trigger("filter_filing_method");
	},

	validate: function (frm) {
		frm.trigger("set_default_company");
		frm.trigger("mobile_no_validation");
	},

	toggle_display_accrual_pto_rate(frm) {
		frm.set_df_property("custom_pto_hours", "hidden", 1);
		frappe.db.get_value("Leave Type", "PTO", "custom_is_accrual_rate").then((r) => {
			if (r.message && r.message.custom_is_accrual_rate) {
				if (frm.doc.date_of_joining) {
					let doj = frappe.datetime.str_to_obj(frm.doc.date_of_joining);
					let today = frappe.datetime.now_date(true);
					let today_obj = frappe.datetime.str_to_obj(today);
					let diff_days = frappe.datetime.get_diff(today_obj, doj);
					if (diff_days >= 90) {
						frm.set_df_property("custom_pto_hours", "hidden", 0);
					}
				}
			}
		});
	},

	cell_number: function (frm) {
		frm.trigger("format_cell_number");
	},

	mobile_no_validation: function (frm) {
		let cell_number = frm.doc.cell_number;
		let cell_number_pattern = /^\(\d{3}\)\d{3}-\d{4}$/;
		if (cell_number) {
			let digits = cell_number.replace(/\D/g, "");
			if (digits.length < 10) {
				frappe.msgprint(__("Mobile Number should be 10 digits."));
			}
		}

		if (cell_number && !cell_number_pattern.test(cell_number)) {
			frappe.msgprint(__("Cell Number must be in the format (xxx)xxx-xxxx"));
			frappe.validated = false;
		}
	},

	format_cell_number: function (frm) {
		let cell_number = frm.doc.cell_number;
		if (cell_number) {
			let digits = cell_number.replace(/\D/g, "");
			if (digits.length === 10) {
				let formatted = `(${digits.substring(0, 3)})${digits.substring(
					3,
					6
				)}-${digits.substring(6, 10)}`;
				frm.set_value("cell_number", formatted);
			}

			if (digits.length > 10) {
				frappe.msgprint(__("Mobile Number should be 10 digits."));
			}
		}
	},

	custom_social_security_number: function (frm) {
		let ssn = frm.doc.custom_social_security_number;
		if (ssn) {
			ssn = ssn.replace(/\D/g, "");
			if (ssn.length === 9) {
				ssn = ssn.replace(/^(\d{3})(\d{2})(\d{4})$/, "$1-$2-$3");
				frm.set_value("custom_social_security_number", ssn);
			} else {
				frappe.msgprint(__("Social Security Number should be 9 digits."));
			}
		}
	},

	before_save: function (frm) {
		let ssn = frm.doc.custom_social_security_number;
		if (ssn) {
			if (ssn.startsWith("XXX-XX-")) {
				return;
			}
			let raw_ssn = ssn.replace(/\D/g, "");
			if (raw_ssn.length === 9) {
				frm.set_value("custom_nomasked_social_security_number", raw_ssn);

				let masked_ssn = "XXX-XX-" + raw_ssn.slice(-4);
				frm.set_value("custom_social_security_number", masked_ssn);
			} else {
				frappe.msgprint(__("Social Security Number should be 9 digits."));
				frm.set_value("custom_social_security_number", "");
				frm.set_value("custom_nomasked_social_security_number", "");
			}
		}
	},

	custom_hourly_rate: function (frm) {
		if (frm.doc.custom_hourly_rate) {
			let hourly_rate = frm.doc.custom_hourly_rate;
			let overtime_rate = hourly_rate * 1.5;
			frm.set_value("custom_overtime_rate", overtime_rate);
		}
	},

	custom_number_of_qualifying__children: function (frm) {
		frm.set_value(
			"custom_children_credit",
			(frm.doc.custom_number_of_qualifying__children || 0) * 2000
		);
		frm.trigger("calculate_total_dependents");
	},
	custom_other_dependents: function (frm) {
		frm.set_value("custom_other_credit", (frm.doc.custom_other_dependents || 0) * 500);
		frm.trigger("calculate_total_dependents");
	},
	calculate_total_dependents: function (frm) {
		frm.set_value(
			"custom_total_credit",
			(frm.doc.custom_children_credit || 0) + (frm.doc.custom_other_credit || 0)
		);
	},

	filter_filing_method: function (frm) {
		if (frm.doc.custom_1a) {
			frm.set_query("custom_filing_method", function (doc) {
				return {
					filters: {
						custom_more_than_one_job: 1,
						docstatus: 1,
					},
				};
			});
		} else {
			frm.set_query("custom_filing_method", function (doc) {
				return {
					filters: {
						custom_more_than_one_job: 0,
						docstatus: 1,
					},
				};
			});
		}
	},

	custom_1a: function (frm) {
		frm.set_value("custom_filing_method", "");
		if (frm.doc.custom_1a) {
			frm.set_query("custom_filing_method", function (doc) {
				return {
					filters: {
						custom_more_than_one_job: 1,
						docstatus: 1,
					},
				};
			});
		} else {
			frm.set_query("custom_filing_method", function (doc) {
				return {
					filters: {
						custom_more_than_one_job: 0,
						docstatus: 1,
					},
				};
			});
		}
	},

	custom_filing_method: function (frm) {
		if (!frm.doc.custom_filing_method || !frm.doc.name) return;
		frappe.db
			.get_list("Salary Structure Assignment", {
				filters: {
					employee: frm.doc.name,
					docstatus: 1,
				},
				fields: ["name"],
				order_by: "from_date desc",
				limit: 1,
			})
			.then((ssa_list) => {
				if (ssa_list.length > 0) {
					let ssa = ssa_list[0];
					frappe.call({
						method: "frappe.client.set_value",
						args: {
							doctype: "Salary Structure Assignment",
							name: ssa.name,
							fieldname: "income_tax_slab",
							value: frm.doc.custom_filing_method,
						},
						callback: function () {
							// Updated Income Tax Slab in Salary Structure Assignment
						},
					});
				}
			});
	},

	set_default_company: function (frm) {
		if (frm.doc.__islocal == 1) {
			frappe.call({
				method: "us_payroll.custom_script.employee.get_global_defaults_values",
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

	custom_payroll_type: function (frm) {
		frm.trigger("toggle_payroll_fields");

		if (frm.doc.custom_payroll_type === "Hourly") {
			frm.set_value("custom_base_amount", 0);
		}
	},

	toggle_payroll_fields: function (frm) {
		if (frm.doc.custom_payroll_type === "Fixed") {
			frm.toggle_display("custom_base_amount", true);
			frm.toggle_display("custom_hourly_rate", false);
		} else if (frm.doc.custom_payroll_type === "Hourly") {
			frm.toggle_display("custom_base_amount", false);
			frm.toggle_display("custom_hourly_rate", true);
		} else {
			frm.toggle_display("custom_base_amount", false);
			frm.toggle_display("custom_hourly_rate", false);
		}
	},
});
