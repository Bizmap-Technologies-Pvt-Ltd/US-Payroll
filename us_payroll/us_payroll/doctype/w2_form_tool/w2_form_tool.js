// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

cur_frm.page.sidebar.toggle();

frappe.ui.form.on("W2 Form Tool", {
	onload: function (frm) {
		// frm.trigger("set_default_year");
		frm.trigger("set_ein");
	},

	refresh: function (frm) {
		frm.disable_save();
		// frm.trigger("set_default_year");
		frm.trigger("set_ein");
		frm.trigger("hide_add_row_btn");

		if (frm.fields_dict.get_employees) {
			frm.fields_dict.get_employees.$wrapper
				.find("button")
				.removeClass("btn-default btn-xs")
				.addClass("btn-primary");
		}

		if (frm.fields_dict.generate_w2_form_records) {
			frm.fields_dict.generate_w2_form_records.$wrapper
				.find("button")
				.removeClass("btn-default btn-xs")
				.addClass("btn-primary");
		}
	},

	hide_add_row_btn: function (frm) {
		$('*[data-fieldname="w2_form_details"]').find(".grid-add-row").remove();
		$('*[data-fieldname="w2_form_details"]').find(".grid-row-check").remove();
	},

	set_default_year: function (frm) {
		if (!frm.doc.year) {
			frm.set_value("year", new Date().getFullYear());
		}
	},

	year: function (frm) {
		if (frm.doc.year) {
			frm.set_value("year_start_date", `${frm.doc.year}-01-01`);
			frm.set_value("year_end_date", `${frm.doc.year}-12-31`);
		}
	},

	set_ein: function (frm) {
		let company = frappe.defaults.get_global_default("company");
		frappe.db.get_value("Company", company, "tax_id", (r) => {
			if (r && r.tax_id) {
				frm.set_value("employer_identification_number_ein", r.tax_id);
			}
		});
	},

	get_employees: function (frm) {
		frappe.call({
			method: "us_payroll.us_payroll.doctype.w2_form_tool.w2_form_tool.get_employees",
			args: { doc: frm.doc },
			freeze: true,
			freeze_message: __("Fetching employees..."),
			callback(r) {
				if (!r.message) return;

				frm.clear_table("w2_form_details");

				r.message.forEach((row) => {
					let d = frm.add_child("w2_form_details");
					d.control_number = row.control_number;
					d.employee = row.employee;
					d.employee_name = row.employee_name;
					d.first_name = row.first_name;
					d.last_name = row.last_name;
					d.social_security_number = row.social_security_number;
					d.address = row.address;

					d.wages_tips_other_compensation = row.wages_tips_other_compensation;
					d.federal_income_tax_withheld = row.federal_income_tax_withheld;
					d.social_security_tax_withheld = row.social_security_tax_withheld;
					d.medicare_tax_withheld = row.medicare_tax_withheld;
					d.tmrs = row.tmrs;
					d.medical_insurance = row.medical_insurance;
					d.social_security_wages = row.social_security_wages;
					d.medicare_wages_and_tips = row.medicare_wages_and_tips;

					if (row.tmrs > 0) {
						d.retirement_plan = true;
					}
				});

				frm.refresh_field("w2_form_details");
			},
		});
	},

	generate_w2_form_records: function (frm) {
		frappe.call({
			method: "us_payroll.us_payroll.doctype.w2_form_tool.w2_form_tool.generate_w2_form_records",
			args: { doc: frm.doc },
			freeze: true,
			freeze_message: __("Generating W2 Form Details..."),
			callback(r) {
				let messages = [];

				if (r.message?.created?.length) {
					r.message.created.forEach((c) => {
						messages.push(
							// __("W2 Form Details record <b>{0}</b> created for employee <b>{1}</b>.", [
							__("W2 Form created for employee <b>{1}</b>.", [
								c.name,
								c.employee_name || c.employee,
								c.year,
							])
						);
					});
				}

				if (r.message?.skipped?.length) {
					r.message.skipped.forEach((s) => {
						messages.push(
							__("W2 record already exists for employee <b>{0}</b> for Year {1}", [
								s.employee_name || s.employee,
								s.year,
							])
						);
					});
				}

				frappe.msgprint({
					title: __("W2 Generation Summary"),
					message: messages.join("<br>"),
					indicator: r.message.created.length ? "green" : "orange",
				});
			},
		});
	},
});
