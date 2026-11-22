// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.ui.form.on("W2 Form Details", {
	refresh: function (frm) {
		// frm.trigger("set_default_year");
		frm.trigger("set_ein");

		if (frm.doc.__islocal == 1) {
			frm.trigger("set_company_address");
		}
	},

	onload: function (frm) {
		// frm.trigger("set_default_year");
		frm.trigger("set_ein");
		if (frm.doc.__islocal == 1) {
			frm.trigger("set_company_address");
		}
	},

	employee: function (frm) {
		if (frm.doc.employee) {
			frappe.db.get_value(
				"Employee",
				frm.doc.employee,
				[
					"name",
					"first_name",
					"last_name",
					"custom_nomasked_social_security_number",
					"employee_name",
					"custom_address_line_1",
					"custom_address_line_2",
					"custom_city",
					"custom_stateprovince",
					"custom_zip_postal_code",
				],
				function (data) {
					if (data) {
						let full_address = `${data.employee_name} \n${
							data.custom_address_line_1 || ""
						} \n${data.custom_address_line_2 || ""}\n${data.custom_city || ""}  ${
							data.custom_stateprovince || ""
						} ${data.custom_zip_postal_code || ""}`;
						frm.set_value("control_number", data.name);
						frm.set_value("first_name", data.first_name);
						frm.set_value("last_name", data.last_name);
						frm.set_value(
							"social_security_number",
							data.custom_nomasked_social_security_number
						);
						frm.set_value("address", full_address);
					}
				}
			);
		}

		frm.trigger("calculate_w2_totals");
	},

	set_ein: function (frm) {
		var company = frappe.defaults.get_global_default("company");
		frappe.db.get_value("Company", company, ["tax_id"], function (data) {
			if (data && frm.doc.__islocal == 1) {
				frm.set_value("employer_identification_number_ein", data.tax_id);
			}
		});
	},

	set_company_address: function (frm) {
		frappe.db
			.get_list("Address", {
				filters: {
					// is_primary_address: 1,
					is_your_company_address: 1,
				},
				fields: [
					"name",
					"address_line1",
					"address_line2",
					"city",
					"state",
					"pincode",
					"country",
				],
				limit: 1,
			})
			.then((addresses) => {
				if (addresses.length) {
					let a = addresses[0];
					let employer_address = `${a.address_line1 || ""}\n ${
						a.address_line2 || ""
					}\n ${a.city || ""}, ${a.state || ""} ${a.pincode || ""}\n ${a.country || ""}`;
					frm.set_value("company_address", employer_address);
				}
			});
	},

	set_default_year: function (frm) {
		let today = new Date();
		let currentYear = today.getFullYear();
		if (frm.doc.__islocal == 1) {
			frm.set_value("year", currentYear);
		}
	},

	calculate_w2_totals: function (frm) {
		if (!frm.doc.employee || !frm.doc.year_start_date || !frm.doc.year_end_date) {
			return;
		}

		frappe.call({
			method: "us_payroll.us_payroll.doctype.w2_form_details.w2_form_details.calculate_totals",
			args: {
				doc: frm.doc,
			},
			callback: function (r) {
				if (!r.message) return;

				const data = r.message;

				frm.set_value({
					wages_tips_other_compensation: data.total_gross_pay,
					federal_income_tax_withheld: data.total_federal_income_tax_withheld,
					social_security_tax_withheld: data.social_security_tax_withheld,
					medicare_tax_withheld: data.medicare_tax_withheld,
					social_security_wages: data.social_security_wages,
					medicare_wages_and_tips: data.medicare_wages_and_tips,
					retirement_plan: data.retirement_plan,
				});

				// Populate W-2 Box 12 child table
				frm.clear_table("box_12_details");

				const box_12_amounts = data.box_12_amounts || {};

				Object.entries(box_12_amounts).forEach(([code, amount]) => {
					frm.add_child("box_12_details", {
						box_12_code: code,
						amount: amount,
					});
				});

				frm.refresh_field("box_12_details");
			},
		});
	},

	year: function (frm) {
		if (!frm.doc.year) return;

		const selectedYear = frm.doc.year;

		frm.set_value({
			year_start_date: `${selectedYear}-01-01`,
			year_end_date: `${selectedYear}-12-31`,
		}).then(() => {
			frm.trigger("calculate_w2_totals");
		});
	},
});
