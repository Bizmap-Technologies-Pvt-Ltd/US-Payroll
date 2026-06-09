// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.ui.form.on("Form 941 Details", {
	refresh: function (frm) {
		frm.trigger("update_quarter_section");
		frm.trigger("show_hide_quarter_sections");
		frm.trigger("set_ein");
		frm.trigger("set_address_details");
	},

	onload: function (frm) {
		frm.trigger("update_quarter_section");
		frm.trigger("show_hide_quarter_sections");
		frm.trigger("set_ein");
		frm.trigger("set_address_details");
	},

	show_hide_quarter_sections: function (frm) {
		frm.set_df_property("report_for_this_quarter_of_2024_check_one_section", "hidden", 1);
		if (frm.doc.year) {
			frm.set_df_property("report_for_this_quarter_of_2024_check_one_section", "hidden", 0);
		} else {
			frm.set_df_property("report_for_this_quarter_of_2024_check_one_section", "hidden", 1);
		}
	},

	year: function (frm) {
		frm.trigger("update_quarter_section");
		frm.trigger("show_hide_quarter_sections");

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

	update_quarter_section: function (frm) {
		if (!frm.doc.year) {
			frm.set_df_property("quarter_section_title", "hidden", 1);
			return;
		}

		frm.set_df_property("quarter_section_title", "hidden", 0);

		frm.fields_dict.quarter_section_title.$wrapper.html(`
            <h3 style="margin-bottom: 11px; font-weight:bold">
                Report for this Quarter of ${frm.doc.year} (Check one.)
            </h1>
        `);
	},

	january_february_march: function (frm) {
		if (frm.doc.january_february_march) {
			frm.set_df_property("april_may_june", "read_only", 1);
			frm.set_df_property("july_august_september", "read_only", 1);
			frm.set_df_property("october_november_december", "read_only", 1);

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.calculate_totals",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_gross_pay = r.message.total_gross_pay;
					let social_security_wages_amt = r.message.social_security_wages_amt;
					let medicare_wages_and_tips = r.message.medicare_wages_and_tips;
					let taxable_wages = r.message.taxable_wages;
					let taxable_wages_medicare = r.message.taxable_wages_medicare;
					let total_federal_income_tax_withheld =
						r.message.total_federal_income_tax_withheld;

					if (r.message) {
						frm.set_value("wages_tips_other_compensation", total_gross_pay);
						frm.set_value("social_security_wages", social_security_wages_amt);
						frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
						frm.set_value("taxable_wages", taxable_wages);
						frm.set_value("taxable_wages_medicare", taxable_wages_medicare);
						frm.set_value(
							"federal_income_tax_withheld",
							total_federal_income_tax_withheld
						);
					} else {
						frm.set_value("wages_tips_other_compensation", "");
						frm.set_value("social_security_wages", "");
						frm.set_value("medicare_wages_and_tips", "");
						frm.set_value("taxable_wages", "");
						frm.set_value("taxable_wages_medicare", "");
						frm.set_value("federal_income_tax_withheld", "");
					}

					frm.refresh_field("wages_tips_other_compensation");
					frm.refresh_field("social_security_wages");
					frm.refresh_field("medicare_wages_and_tips");
					frm.refresh_field("taxable_wages");
					frm.refresh_field("taxable_wages_medicare");
					frm.refresh_field("federal_income_tax_withheld");
				},
			});

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.get_quarterly_data_for_liability",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_taxes_after_adjustments = r.message.total_amt;
					if (total_taxes_after_adjustments) {
						frm.set_value(
							"total_taxes_after_adjustments",
							total_taxes_after_adjustments
						);
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							total_taxes_after_adjustments
						);
						frm.set_value("balance_due", total_taxes_after_adjustments);
					} else {
						frm.set_value("total_taxes_after_adjustments", "");
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							""
						);
						frm.set_value("balance_due", "");
					}

					let number_of_employees = r.message.employee_count;
					if (number_of_employees) {
						frm.set_value("number_of_employees", number_of_employees);
					} else {
						frm.set_value("number_of_employees", "");
					}

					let first_month = r.message.first_month;
					let second_month = r.message.second_month;
					let third_month = r.message.third_month;

					frm.set_value("first_month", first_month);
					frm.set_value("second_month", second_month);
					frm.set_value("third_month", third_month);

					frm.refresh_field("total_taxes_after_adjustments");
					frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
					frm.refresh_field("balance_due");
					frm.refresh_field("number_of_employees");
					frm.refresh_field("first_month");
					frm.refresh_field("second_month");
					frm.refresh_field("third_month");
				},
			});
		} else {
			frm.set_df_property("april_may_june", "read_only", 0);
			frm.set_df_property("july_august_september", "read_only", 0);
			frm.set_df_property("october_november_december", "read_only", 0);

			frm.set_value("wages_tips_other_compensation", "");
			frm.set_value("federal_income_tax_withheld", "");
			frm.set_value("social_security_wages", "");
			frm.set_value("medicare_wages_and_tips", "");
			frm.set_value("taxable_wages", "");
			frm.set_value("taxable_wages_medicare", "");
			frm.set_value("total_taxes_after_adjustments", "");
			frm.set_value("total_taxes_after_adjustments_and_nonrefundable_credits", "");
			frm.set_value("balance_due", "");
			frm.set_value("number_of_employees", "");
			frm.set_value("first_month", "");
			frm.set_value("second_month", "");
			frm.set_value("third_month", "");
		}
		frm.refresh_field("wages_tips_other_compensation");
		frm.refresh_field("federal_income_tax_withheld");
		frm.refresh_field("social_security_wages");
		frm.refresh_field("medicare_wages_and_tips");
		frm.refresh_field("taxable_wages");
		frm.refresh_field("taxable_wages_medicare");
		frm.refresh_field("total_taxes_after_adjustments");
		frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
		frm.refresh_field("balance_due");
		frm.refresh_field("number_of_employees");
		frm.refresh_field("first_month");
		frm.refresh_field("second_month");
		frm.refresh_field("third_month");
	},

	april_may_june: function (frm) {
		frm.set_df_property("january_february_march", "read_only", 1);
		frm.set_df_property("july_august_september", "read_only", 1);
		frm.set_df_property("october_november_december", "read_only", 1);

		if (frm.doc.april_may_june) {
			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.calculate_totals",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_gross_pay = r.message.total_gross_pay;
					let social_security_wages_amt = r.message.social_security_wages_amt;
					let medicare_wages_and_tips = r.message.medicare_wages_and_tips;
					let taxable_wages = r.message.taxable_wages;
					let taxable_wages_medicare = r.message.taxable_wages_medicare;
					let total_federal_income_tax_withheld =
						r.message.total_federal_income_tax_withheld;

					if (r.message) {
						frm.set_value("wages_tips_other_compensation", total_gross_pay);
						frm.set_value("social_security_wages", social_security_wages_amt);
						frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
						frm.set_value("taxable_wages", taxable_wages);
						frm.set_value("taxable_wages_medicare", taxable_wages_medicare);
						frm.set_value(
							"federal_income_tax_withheld",
							total_federal_income_tax_withheld
						);
					} else {
						frm.set_value("wages_tips_other_compensation", "");
						frm.set_value("social_security_wages", "");
						frm.set_value("medicare_wages_and_tips", "");
						frm.set_value("taxable_wages", "");
						frm.set_value("taxable_wages_medicare", "");
						frm.set_value("federal_income_tax_withheld", "");
					}

					frm.refresh_field("wages_tips_other_compensation");
					frm.refresh_field("social_security_wages");
					frm.refresh_field("medicare_wages_and_tips");
					frm.refresh_field("taxable_wages");
					frm.refresh_field("taxable_wages_medicare");
					frm.refresh_field("federal_income_tax_withheld");
				},
			});

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.get_quarterly_data_for_liability",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_taxes_after_adjustments = r.message.total_amt;
					if (total_taxes_after_adjustments) {
						frm.set_value(
							"total_taxes_after_adjustments",
							total_taxes_after_adjustments
						);
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							total_taxes_after_adjustments
						);
						frm.set_value("balance_due", total_taxes_after_adjustments);
					} else {
						frm.set_value("total_taxes_after_adjustments", "");
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							""
						);
						frm.set_value("balance_due", "");
					}

					let number_of_employees = r.message.employee_count;
					if (number_of_employees) {
						frm.set_value("number_of_employees", number_of_employees);
					} else {
						frm.set_value("number_of_employees", "");
					}

					let first_month = r.message.first_month;
					let second_month = r.message.second_month;
					let third_month = r.message.third_month;

					frm.set_value("first_month", first_month);
					frm.set_value("second_month", second_month);
					frm.set_value("third_month", third_month);

					frm.refresh_field("total_taxes_after_adjustments");
					frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
					frm.refresh_field("balance_due");
					frm.refresh_field("number_of_employees");
					frm.refresh_field("first_month");
					frm.refresh_field("second_month");
					frm.refresh_field("third_month");
				},
			});
		} else {
			frm.set_df_property("january_february_march", "read_only", 0);
			frm.set_df_property("july_august_september", "read_only", 0);
			frm.set_df_property("october_november_december", "read_only", 0);

			frm.set_value("wages_tips_other_compensation", "");
			frm.set_value("federal_income_tax_withheld", "");
			frm.set_value("social_security_wages", "");
			frm.set_value("medicare_wages_and_tips", "");
			frm.set_value("taxable_wages", "");
			frm.set_value("taxable_wages_medicare", "");
			frm.set_value("total_taxes_after_adjustments", "");
			frm.set_value("total_taxes_after_adjustments_and_nonrefundable_credits", "");
			frm.set_value("balance_due", "");
			frm.set_value("number_of_employees", "");
			frm.set_value("first_month", "");
			frm.set_value("second_month", "");
			frm.set_value("third_month", "");
		}

		frm.refresh_field("wages_tips_other_compensation");
		frm.refresh_field("federal_income_tax_withheld");
		frm.refresh_field("social_security_wages");
		frm.refresh_field("medicare_wages_and_tips");
		frm.refresh_field("taxable_wages");
		frm.refresh_field("taxable_wages_medicare");
		frm.refresh_field("total_taxes_after_adjustments");
		frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
		frm.refresh_field("balance_due");
		frm.refresh_field("number_of_employees");
		frm.refresh_field("first_month");
		frm.refresh_field("second_month");
		frm.refresh_field("third_month");
	},

	july_august_september: function (frm) {
		if (frm.doc.july_august_september) {
			frm.set_df_property("january_february_march", "read_only", 1);
			frm.set_df_property("april_may_june", "read_only", 1);
			frm.set_df_property("october_november_december", "read_only", 1);

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.calculate_totals",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_gross_pay = r.message.total_gross_pay;
					let social_security_wages_amt = r.message.social_security_wages_amt;
					let medicare_wages_and_tips = r.message.medicare_wages_and_tips;
					let taxable_wages = r.message.taxable_wages;
					let taxable_wages_medicare = r.message.taxable_wages_medicare;
					let total_federal_income_tax_withheld =
						r.message.total_federal_income_tax_withheld;

					if (r.message) {
						frm.set_value("wages_tips_other_compensation", total_gross_pay);
						frm.set_value("social_security_wages", social_security_wages_amt);
						frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
						frm.set_value("taxable_wages", taxable_wages);
						frm.set_value("taxable_wages_medicare", taxable_wages_medicare);
						frm.set_value(
							"federal_income_tax_withheld",
							total_federal_income_tax_withheld
						);
					} else {
						frm.set_value("wages_tips_other_compensation", "");
						frm.set_value("social_security_wages", "");
						frm.set_value("medicare_wages_and_tips", "");
						frm.set_value("taxable_wages", "");
						frm.set_value("taxable_wages_medicare", "");
						frm.set_value("federal_income_tax_withheld", "");
					}

					frm.refresh_field("wages_tips_other_compensation");
					frm.refresh_field("social_security_wages");
					frm.refresh_field("medicare_wages_and_tips");
					frm.refresh_field("taxable_wages");
					frm.refresh_field("taxable_wages_medicare");
					frm.refresh_field("federal_income_tax_withheld");
				},
			});

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.get_quarterly_data_for_liability",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_taxes_after_adjustments = r.message.total_amt;
					if (total_taxes_after_adjustments) {
						frm.set_value(
							"total_taxes_after_adjustments",
							total_taxes_after_adjustments
						);
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							total_taxes_after_adjustments
						);
						frm.set_value("balance_due", total_taxes_after_adjustments);
					} else {
						frm.set_value("total_taxes_after_adjustments", "");
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							""
						);
						frm.set_value("balance_due", "");
					}

					let number_of_employees = r.message.employee_count;
					if (number_of_employees) {
						frm.set_value("number_of_employees", number_of_employees);
					} else {
						frm.set_value("number_of_employees", "");
					}

					let first_month = r.message.first_month;
					let second_month = r.message.second_month;
					let third_month = r.message.third_month;

					frm.set_value("first_month", first_month);
					frm.set_value("second_month", second_month);
					frm.set_value("third_month", third_month);

					frm.refresh_field("total_taxes_after_adjustments");
					frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
					frm.refresh_field("balance_due");
					frm.refresh_field("number_of_employees");
					frm.refresh_field("first_month");
					frm.refresh_field("second_month");
					frm.refresh_field("third_month");
				},
			});
		} else {
			frm.set_df_property("january_february_march", "read_only", 0);
			frm.set_df_property("april_may_june", "read_only", 0);
			frm.set_df_property("october_november_december", "read_only", 0);

			frm.set_value("wages_tips_other_compensation", "");
			frm.set_value("federal_income_tax_withheld", "");
			frm.set_value("social_security_wages", "");
			frm.set_value("medicare_wages_and_tips", "");
			frm.set_value("taxable_wages", "");
			frm.set_value("taxable_wages_medicare", "");
			frm.set_value("total_taxes_after_adjustments", "");
			frm.set_value("total_taxes_after_adjustments_and_nonrefundable_credits", "");
			frm.set_value("balance_due", "");
			frm.set_value("number_of_employees", "");
			frm.set_value("first_month", "");
			frm.set_value("second_month", "");
			frm.set_value("third_month", "");
		}

		frm.refresh_field("wages_tips_other_compensation");
		frm.refresh_field("federal_income_tax_withheld");
		frm.refresh_field("social_security_wages");
		frm.refresh_field("medicare_wages_and_tips");
		frm.refresh_field("taxable_wages");
		frm.refresh_field("taxable_wages_medicare");
		frm.refresh_field("total_taxes_after_adjustments");
		frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
		frm.refresh_field("balance_due");
		frm.refresh_field("number_of_employees");
		frm.refresh_field("first_month");
		frm.refresh_field("second_month");
		frm.refresh_field("third_month");
	},

	october_november_december: function (frm) {
		if (frm.doc.october_november_december) {
			frm.set_df_property("january_february_march", "read_only", 1);
			frm.set_df_property("july_august_september", "read_only", 1);
			frm.set_df_property("april_may_june", "read_only", 1);

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.calculate_totals",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_gross_pay = r.message.total_gross_pay;
					let social_security_wages_amt = r.message.social_security_wages_amt;
					let medicare_wages_and_tips = r.message.medicare_wages_and_tips;
					let taxable_wages = r.message.taxable_wages;
					let taxable_wages_medicare = r.message.taxable_wages_medicare;
					let total_federal_income_tax_withheld =
						r.message.total_federal_income_tax_withheld;

					if (r.message) {
						frm.set_value("wages_tips_other_compensation", total_gross_pay);
						frm.set_value("social_security_wages", social_security_wages_amt);
						frm.set_value("medicare_wages_and_tips", medicare_wages_and_tips);
						frm.set_value("taxable_wages", taxable_wages);
						frm.set_value("taxable_wages_medicare", taxable_wages_medicare);
						frm.set_value(
							"federal_income_tax_withheld",
							total_federal_income_tax_withheld
						);
					} else {
						frm.set_value("wages_tips_other_compensation", "");
						frm.set_value("social_security_wages", "");
						frm.set_value("medicare_wages_and_tips", "");
						frm.set_value("taxable_wages", "");
						frm.set_value("taxable_wages_medicare", "");
						frm.set_value("federal_income_tax_withheld", "");
					}

					frm.refresh_field("wages_tips_other_compensation");
					frm.refresh_field("social_security_wages");
					frm.refresh_field("medicare_wages_and_tips");
					frm.refresh_field("taxable_wages");
					frm.refresh_field("taxable_wages_medicare");
					frm.refresh_field("federal_income_tax_withheld");
				},
			});

			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.get_quarterly_data_for_liability",
				args: {
					doc: frm.doc,
				},
				callback: function (r) {
					let total_taxes_after_adjustments = r.message.total_amt;
					if (total_taxes_after_adjustments) {
						frm.set_value(
							"total_taxes_after_adjustments",
							total_taxes_after_adjustments
						);
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							total_taxes_after_adjustments
						);
						frm.set_value("balance_due", total_taxes_after_adjustments);
					} else {
						frm.set_value("total_taxes_after_adjustments", "");
						frm.set_value(
							"total_taxes_after_adjustments_and_nonrefundable_credits",
							""
						);
						frm.set_value("balance_due", "");
					}

					let number_of_employees = r.message.employee_count;
					if (number_of_employees) {
						frm.set_value("number_of_employees", number_of_employees);
					} else {
						frm.set_value("number_of_employees", "");
					}

					let first_month = r.message.first_month;
					let second_month = r.message.second_month;
					let third_month = r.message.third_month;

					frm.set_value("first_month", first_month);
					frm.set_value("second_month", second_month);
					frm.set_value("third_month", third_month);

					frm.refresh_field("total_taxes_after_adjustments");
					frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
					frm.refresh_field("balance_due");
					frm.refresh_field("number_of_employees");
					frm.refresh_field("first_month");
					frm.refresh_field("second_month");
					frm.refresh_field("third_month");
				},
			});
		} else {
			frm.set_df_property("january_february_march", "read_only", 0);
			frm.set_df_property("july_august_september", "read_only", 0);
			frm.set_df_property("april_may_june", "read_only", 0);

			frm.set_value("wages_tips_other_compensation", "");
			frm.set_value("federal_income_tax_withheld", "");
			frm.set_value("social_security_wages", "");
			frm.set_value("medicare_wages_and_tips", "");
			frm.set_value("taxable_wages", "");
			frm.set_value("taxable_wages_medicare", "");
			frm.set_value("total_taxes_after_adjustments", "");
			frm.set_value("total_taxes_after_adjustments_and_nonrefundable_credits", "");
			frm.set_value("balance_due", "");
			frm.set_value("number_of_employees", "");
			frm.set_value("first_month", "");
			frm.set_value("second_month", "");
			frm.set_value("third_month", "");
		}

		frm.refresh_field("wages_tips_other_compensation");
		frm.refresh_field("federal_income_tax_withheld");
		frm.refresh_field("social_security_wages");
		frm.refresh_field("medicare_wages_and_tips");
		frm.refresh_field("taxable_wages");
		frm.refresh_field("taxable_wages_medicare");
		frm.refresh_field("total_taxes_after_adjustments");
		frm.refresh_field("total_taxes_after_adjustments_and_nonrefundable_credits");
		frm.refresh_field("balance_due");
		frm.refresh_field("number_of_employees");
		frm.refresh_field("first_month");
		frm.refresh_field("second_month");
		frm.refresh_field("third_month");
	},

	social_security_wages: function (frm) {
		if (frm.doc.social_security_wages) {
			let total_amount = frm.doc.social_security_wages + frm.doc.medicare_wages_and_tips;
			frm.set_value("total_social_security_and_medicare_taxes", total_amount);
		}
	},

	medicare_wages_and_tips: function (frm) {
		if (frm.doc.medicare_wages_and_tips) {
			let total_amount = frm.doc.social_security_wages + frm.doc.medicare_wages_and_tips;
			frm.set_value("total_social_security_and_medicare_taxes", total_amount);
		}
	},

	total_social_security_and_medicare_taxes: function (frm) {
		if (frm.doc.total_social_security_and_medicare_taxes) {
			let total_amount =
				frm.doc.total_social_security_and_medicare_taxes +
				frm.doc.federal_income_tax_withheld;
			frm.set_value("total_taxes_before_adjustments", total_amount);
		}
	},

	federal_income_tax_withheld: function (frm) {
		if (frm.doc.federal_income_tax_withheld) {
			let total_amount =
				frm.doc.total_social_security_and_medicare_taxes +
				frm.doc.federal_income_tax_withheld;
			frm.set_value("total_taxes_before_adjustments", total_amount);
		}
	},

	set_ein: function (frm) {
		var company = frappe.defaults.get_global_default("company");
		frappe.db.get_value("Company", company, ["tax_id"], function (data) {
			if (data) {
				frm.set_value("employer_identification_number_ein", data.tax_id);
			}
		});
	},

	set_address_details: function (frm) {
		if (frm.doc.employer_name && frm.doc.__islocal == 1) {
			frappe.call({
				method: "us_payroll.us_payroll.doctype.form_941_details.form_941_details.fetch_address_details",
				args: {
					is_your_company_address: 1,
					link_doctype: "Company",
					link_name: frm.doc.employer_name,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("address_line_1", r.message.address_line1);
						frm.set_value("city", r.message.city);
						frm.set_value("state", r.message.state);
						frm.set_value("foreign_country_name", r.message.country);
						frm.set_value("foreign_provincecounty", r.message.county);
						frm.set_value("foreign_postal_code", r.message.pincode);
					}
				},
			});
		}
	},

	employer_identification_number_ein: function (frm) {
		let ein = frm.doc.employer_identification_number_ein;
		if (ein && ein.length === 9 && frm.doc.__islocal == 1) {
			frm.set_value("digit1", ein[0]);
			frm.set_value("digit2", ein[1]);
			frm.set_value("digit3", ein[2]);
			frm.set_value("digit4", ein[3]);
			frm.set_value("digit5", ein[4]);
			frm.set_value("digit6", ein[5]);
			frm.set_value("digit7", ein[6]);
			frm.set_value("digit8", ein[7]);
			frm.set_value("digit9", ein[8]);
		} else {
			frappe.msgprint(__("Please enter a valid 9-digit EIN number."));
			frm.set_value("digit1", "");
			frm.set_value("digit2", "");
			frm.set_value("digit3", "");
			frm.set_value("digit4", "");
			frm.set_value("digit5", "");
			frm.set_value("digit6", "");
			frm.set_value("digit7", "");
			frm.set_value("digit8", "");
			frm.set_value("digit9", "");
		}
	},
});
