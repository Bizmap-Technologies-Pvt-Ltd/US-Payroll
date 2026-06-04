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

		frappe.call({
			method: "us_payroll.us_payroll.doctype.w2_form_details.w2_form_details.calculate_totals",
			args: {
				doc: frm.doc,
			},
			callback: function (r) {
				total_gross_pay = r.message.total_gross_pay;
				total_federal_income_tax_withheld = r.message.total_federal_income_tax_withheld;
				social_security_tax_withheld = r.message.social_security_tax_withheld;
				medicare_tax_withheld = r.message.medicare_tax_withheld;
				tmrs = r.message.tmrs;
				medical_insurance = r.message.medical_insurance;
				retirement_plan = r.message.retirement_plan;
				social_security_wages = r.message.social_security_wages;
				medicare_wages_and_tips = r.message.medicare_wages_and_tips;

				if (r.message) {
					frm.set_value("wages_tips_other_compensation", total_gross_pay);
					frm.set_value(
						"federal_income_tax_withheld",
						total_federal_income_tax_withheld
					);
					frm.set_value("social_security_tax_withheld", social_security_tax_withheld);
					frm.set_value("medicare_tax_withheld", medicare_tax_withheld);
					frm.set_value("medical_insurance", medical_insurance);
					frm.set_value("tmrs", tmrs);
					frm.set_value("retirement_plan", retirement_plan);
					frm.set_value("social_security_wages", social_security_wages);
					frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
				} else {
					frm.set_value("wages_tips_other_compensation", "");
					frm.set_value("federal_income_tax_withheld", "");
					frm.set_value("social_security_tax_withheld", "");
					frm.set_value("medicare_tax_withheld", "");
					frm.set_value("medical_insurance", "");
					frm.set_value("tmrs", "");
					frm.set_value("retirement_plan", false);
					frm.set_value("social_security_wages", "");
					frm.set_value("medicare_wages_and_tips", "");
				}
				frm.refresh_field("wages_tips_other_compensation");
				frm.refresh_field("federal_income_tax_withheld");
				frm.refresh_field("social_security_tax_withheld");
				frm.refresh_field("medicare_tax_withheld");
				frm.refresh_field("medical_insurance");
				frm.refresh_field("tmrs");
				frm.refresh_field("retirement_plan");
				frm.refresh_field("social_security_wages");
				frm.refresh_field("medicare_wages_and_tips");
			},
		});
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

	year: function (frm) {
		let today = new Date();
		let currentYear = today.getFullYear();
		let selectedYear = frm.doc.year;
		let fromDateStr = `${selectedYear}/01/01`;
		let fromDate = new Date(fromDateStr);
		let toDateStr = `${selectedYear}/12/31`;
		let toDate = new Date(toDateStr);
		frm.set_value("year_start_date", fromDateStr);
		frm.set_value("year_end_date", toDateStr);

		frappe.call({
			method: "us_payroll.us_payroll.doctype.w2_form_details.w2_form_details.calculate_totals",
			args: {
				doc: frm.doc,
			},
			callback: function (r) {
				total_gross_pay = r.message.total_gross_pay;
				total_federal_income_tax_withheld = r.message.total_federal_income_tax_withheld;
				social_security_tax_withheld = r.message.social_security_tax_withheld;
				medicare_tax_withheld = r.message.medicare_tax_withheld;
				tmrs = r.message.tmrs;
				medical_insurance = r.message.medical_insurance;
				retirement_plan = r.message.retirement_plan;
				social_security_wages = r.message.social_security_wages;
				medicare_wages_and_tips = r.message.medicare_wages_and_tips;

				if (r.message) {
					frm.set_value("wages_tips_other_compensation", total_gross_pay);
					frm.set_value(
						"federal_income_tax_withheld",
						total_federal_income_tax_withheld
					);
					frm.set_value("social_security_tax_withheld", social_security_tax_withheld);
					frm.set_value("medicare_tax_withheld", medicare_tax_withheld);
					frm.set_value("medical_insurance", medical_insurance);
					frm.set_value("tmrs", tmrs);
					frm.set_value("retirement_plan", retirement_plan);
					frm.set_value("social_security_wages", social_security_wages);
					frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
				} else {
					frm.set_value("wages_tips_other_compensation", "");
					frm.set_value("federal_income_tax_withheld", "");
					frm.set_value("social_security_tax_withheld", "");
					frm.set_value("medicare_tax_withheld", "");
					frm.set_value("medical_insurance", "");
					frm.set_value("tmrs", "");
					frm.set_value("retirement_plan", false);
					frm.set_value("social_security_wages", "");
					frm.set_value("medicare_wages_and_tips", "");
				}
				frm.refresh_field("wages_tips_other_compensation");
				frm.refresh_field("federal_income_tax_withheld");
				frm.refresh_field("social_security_tax_withheld");
				frm.refresh_field("medicare_tax_withheld");
				frm.refresh_field("medical_insurance");
				frm.refresh_field("tmrs");
				frm.refresh_field("retirement_plan");
				frm.refresh_field("social_security_wages");
				frm.refresh_field("medicare_wages_and_tips");
			},
		});
	},

	// year_start_date: function(frm) {
	// 	frappe.call({
	// 		method: "us_payroll.us_payroll.doctype.w2_form_details.w2_form_details.calculate_totals",
	// 		args: {
	// 			doc: frm.doc
	// 		},
	// 		callback: function(r) {
	// 			total_gross_pay = r.message.total_gross_pay
	// 			total_federal_income_tax_withheld = r.message.total_federal_income_tax_withheld
	// 			social_security_tax_withheld = r.message.social_security_tax_withheld
	// 			medicare_tax_withheld = r.message.medicare_tax_withheld
	// 			tmrs = r.message.tmrs
	// 			medical_insurance = r.message.medical_insurance
	// 			retirement_plan = r.message.retirement_plan

	// 			if (r.message) {
	// 				frm.set_value("wages_tips_other_compensation", total_gross_pay)
	// 				frm.set_value("federal_income_tax_withheld", total_federal_income_tax_withheld)
	// 				frm.set_value("social_security_tax_withheld", social_security_tax_withheld)
	// 				frm.set_value("medicare_tax_withheld", medicare_tax_withheld)
	// 				frm.set_value("medical_insurance", medical_insurance)
	// 				frm.set_value("tmrs", tmrs)
	// 				frm.set_value("retirement_plan", retirement_plan)

	// 			} else {
	// 				frm.set_value("wages_tips_other_compensation", "")
	// 				frm.set_value("federal_income_tax_withheld", "")
	// 				frm.set_value("social_security_tax_withheld", "")
	// 				frm.set_value("medicare_tax_withheld", "")
	// 				frm.set_value("medical_insurance", "")
	// 				frm.set_value("tmrs", "")
	// 				frm.set_value("retirement_plan", false)

	// 			}
	// 			frm.refresh_field("wages_tips_other_compensation");
	// 			frm.refresh_field("federal_income_tax_withheld");
	// 			frm.refresh_field("social_security_tax_withheld");
	// 			frm.refresh_field("medicare_tax_withheld");
	// 			frm.refresh_field("medical_insurance");
	// 			frm.refresh_field("tmrs");
	// 			frm.refresh_field("retirement_plan");
	// 		}
	// 	});
	// },

	// year_end_date: function(frm) {
	// 	frappe.call({
	// 		method: "us_payroll.us_payroll.doctype.w2_form_details.w2_form_details.calculate_totals",
	// 		args: {
	// 			doc: frm.doc
	// 		},
	// 		callback: function(r) {
	// 			total_gross_pay = r.message.total_gross_pay
	// 			total_federal_income_tax_withheld = r.message.total_federal_income_tax_withheld
	// 			social_security_tax_withheld = r.message.social_security_tax_withheld
	// 			medicare_tax_withheld = r.message.medicare_tax_withheld
	// 			tmrs = r.message.tmrs
	// 			medical_insurance = r.message.medical_insurance
	// 			retirement_plan = r.message.retirement_plan

	// 			if (r.message) {
	// 				frm.set_value("wages_tips_other_compensation", total_gross_pay)
	// 				frm.set_value("federal_income_tax_withheld", total_federal_income_tax_withheld)
	// 				frm.set_value("social_security_tax_withheld", social_security_tax_withheld)
	// 				frm.set_value("medicare_tax_withheld", medicare_tax_withheld)
	// 				frm.set_value("medical_insurance", medical_insurance)
	// 				frm.set_value("tmrs", tmrs)
	// 				frm.set_value("retirement_plan", retirement_plan)

	// 			} else {
	// 				frm.set_value("wages_tips_other_compensation", "")
	// 				frm.set_value("federal_income_tax_withheld", "")
	// 				frm.set_value("social_security_tax_withheld", "")
	// 				frm.set_value("medicare_tax_withheld", "")
	// 				frm.set_value("medical_insurance", "")
	// 				frm.set_value("tmrs", "")
	// 				frm.set_value("retirement_plan", false)

	// 			}
	// 			frm.refresh_field("wages_tips_other_compensation");
	// 			frm.refresh_field("federal_income_tax_withheld");
	// 			frm.refresh_field("social_security_tax_withheld");
	// 			frm.refresh_field("medicare_tax_withheld");
	// 			frm.refresh_field("medical_insurance");
	// 			frm.refresh_field("tmrs");
	// 			frm.refresh_field("retirement_plan");
	// 		}
	// 	});
	// },
});
