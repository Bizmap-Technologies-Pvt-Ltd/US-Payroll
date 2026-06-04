// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.ui.form.on("W3 Form Details", {
	refresh: function (frm) {
		frm.trigger("set_employer_name");
		// frm.trigger("set_default_year");
		frm.trigger("set_ein");
		frm.trigger("set_address_and_contact_details");
	},

	onload: function (frm) {
		frm.trigger("set_employer_name");
		// frm.trigger("set_default_year");
		frm.trigger("set_ein");
		frm.trigger("set_address_and_contact_details");
	},

	set_employer_name: function (frm) {
		if (frm.doc.__islocal == 1) {
			frappe.call({
				method: "us_payroll.us_payroll.doctype.w3_form_details.w3_form_details.get_global_defaults_values",
				args: {
					doctype: "Global Defaults",
				},
				callback: function (r) {
					if (r.message && frm.doc.__islocal == 1) {
						default_company = r.message.company;
						frm.set_value("employer_name", default_company);
					}
				},
			});
		}
	},

	set_ein: function (frm) {
		var company = frappe.defaults.get_global_default("company");
		frappe.db.get_value("Company", company, ["tax_id"], function (data) {
			if (data && frm.doc.__islocal == 1) {
				frm.set_value("employer_identification_number_ein", data.tax_id);
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
	},

	year_start_date: function (frm) {
		frappe.call({
			method: "us_payroll.us_payroll.doctype.w3_form_details.w3_form_details.calculate_totals",
			args: {
				doc: frm.doc,
			},
			callback: function (r) {
				wages_tips_other_compensation = r.message.wages_tips_other_compensation;
				total_federal_income_tax_withheld = r.message.total_federal_income_tax_withheld;
				social_security_tax_withheld = r.message.social_security_tax_withheld;
				medicare_tax_withheld = r.message.medicare_tax_withheld;
				number_of_w2_forms = r.message.number_of_w2_forms;
				tmrs = r.message.tmrs;
				medical_insurance = r.message.medical_insurance;
				retirement_plan = r.message.retirement_plan;
				social_security_wages = r.message.social_security_wages;
				medicare_wages_and_tips = r.message.medicare_wages_and_tips;

				if (r.message) {
					frm.set_value("wages_tips_other_compensation", wages_tips_other_compensation);
					frm.set_value(
						"federal_income_tax_withheld",
						total_federal_income_tax_withheld
					);
					frm.set_value("social_security_tax_withheld", social_security_tax_withheld);
					frm.set_value("medicare_tax_withheld", medicare_tax_withheld);
					frm.set_value("number_of_w2_forms", number_of_w2_forms);
					frm.set_value("social_security_wages", social_security_wages);
					frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
				} else {
					frm.set_value("wages_tips_other_compensation", "");
					frm.set_value("federal_income_tax_withheld", "");
					frm.set_value("social_security_tax_withheld", "");
					frm.set_value("medicare_tax_withheld", "");
					frm.set_value("number_of_w2_forms", "");
					frm.set_value("social_security_wages", "");
					frm.set_value("medicare_wages_and_tips", "");
				}
				frm.refresh_field("wages_tips_other_compensation");
				frm.refresh_field("federal_income_tax_withheld");
				frm.refresh_field("social_security_tax_withheld");
				frm.refresh_field("medicare_tax_withheld");
				frm.refresh_field("number_of_w2_forms");
				frm.refresh_field("social_security_wages");
				frm.refresh_field("medicare_wages_and_tips");
			},
		});
	},

	year_end_date: function (frm) {
		frappe.call({
			method: "us_payroll.us_payroll.doctype.w3_form_details.w3_form_details.calculate_totals",
			args: {
				doc: frm.doc,
			},
			callback: function (r) {
				wages_tips_other_compensation = r.message.wages_tips_other_compensation;
				total_federal_income_tax_withheld = r.message.total_federal_income_tax_withheld;
				social_security_tax_withheld = r.message.social_security_tax_withheld;
				medicare_tax_withheld = r.message.medicare_tax_withheld;
				number_of_w2_forms = r.message.number_of_w2_forms;
				tmrs = r.message.tmrs;
				medical_insurance = r.message.medical_insurance;
				retirement_plan = r.message.retirement_plan;
				social_security_wages = r.message.social_security_wages;
				medicare_wages_and_tips = r.message.medicare_wages_and_tips;

				if (r.message) {
					frm.set_value("wages_tips_other_compensation", wages_tips_other_compensation);
					frm.set_value(
						"federal_income_tax_withheld",
						total_federal_income_tax_withheld
					);
					frm.set_value("social_security_tax_withheld", social_security_tax_withheld);
					frm.set_value("medicare_tax_withheld", medicare_tax_withheld);
					frm.set_value("number_of_w2_forms", number_of_w2_forms);
					frm.set_value("social_security_wages", social_security_wages);
					frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
				} else {
					frm.set_value("wages_tips_other_compensation", "");
					frm.set_value("federal_income_tax_withheld", "");
					frm.set_value("social_security_tax_withheld", "");
					frm.set_value("medicare_tax_withheld", "");
					frm.set_value("number_of_w2_forms", "");
					frm.set_value("social_security_wages", "");
					frm.set_value("medicare_wages_and_tips", "");
				}
				frm.refresh_field("wages_tips_other_compensation");
				frm.refresh_field("federal_income_tax_withheld");
				frm.refresh_field("social_security_tax_withheld");
				frm.refresh_field("medicare_tax_withheld");
				frm.refresh_field("number_of_w2_forms");
				frm.refresh_field("social_security_wages");
				frm.refresh_field("medicare_wages_and_tips");
			},
		});
	},

	set_address_and_contact_details: function (frm) {
		// var company = frappe.defaults.get_global_default("company");
		if (frm.doc.employer_name) {
			frappe.call({
				method: "us_payroll.us_payroll.doctype.w3_form_details.w3_form_details.fetch_address_details",
				args: {
					is_your_company_address: 1,
					link_doctype: "Company",
					link_name: frm.doc.employer_name,
				},
				callback: function (r) {
					if (r.message && frm.doc.__islocal == 1) {
						frm.set_value("address", r.message.complete_address);
						frm.set_value("state", r.message.state);
						frm.set_value("employer_contact_person", "");
						frm.set_value("employer_email_address", r.message.email_id);
						frm.set_value("employer_telephone_number", r.message.phone);
						frm.set_value("employer_fax_number", r.message.fax);
					}
				},
			});
		}
	},
});
