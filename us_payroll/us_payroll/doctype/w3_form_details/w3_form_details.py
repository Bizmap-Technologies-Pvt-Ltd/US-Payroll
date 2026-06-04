# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class W3FormDetails(Document):
	pass


@frappe.whitelist()
def calculate_totals(doc):
	doc = json.loads(doc)
	if not (doc.get("year_start_date") and doc.get("year_end_date")):
		frappe.throw("Please make sure Year Start Date and Year End Date are set.")

	year_start_date = doc.get("year_start_date")
	year_end_date = doc.get("year_end_date")

	salary_slips = frappe.get_all(
		"Salary Slip",
		filters={"posting_date": ["between", [year_start_date, year_end_date]], "docstatus": 1},
		fields=[
			"name",
			"gross_pay",
			"custom_taxable_wages",
			"custom_total_non_taxable_earnings",
			"custom_ss_taxable_wages",
			"custom_mc_taxable_wages",
		],
	)

	wages_tips_other_compensation = 0.0
	total_federal_income_tax_withheld = 0.0
	social_security_tax_withheld = 0.0
	medicare_tax_withheld = 0.0
	social_security_wages = 0.0
	medicare_wages_and_tips = 0.0

	for slip in salary_slips:
		# --- Wages, tips, other compensation ---
		if slip.custom_taxable_wages:
			wages_tips_other_compensation += slip.custom_taxable_wages
		else:
			non_taxable = slip.custom_total_non_taxable_earnings or 0
			wages = (slip.gross_pay or 0) - non_taxable
			wages_tips_other_compensation += wages

		salary_slip_doc = frappe.get_doc("Salary Slip", slip.name)

		# --- Social Security Wages ---
		if slip.custom_ss_taxable_wages and slip.custom_ss_taxable_wages > 0:
			social_security_wages += slip.custom_ss_taxable_wages
		else:
			ss_emp = sum(
				d.amount
				for d in salary_slip_doc.deductions
				if d.salary_component == "Social Security Tax - Employee"
			)
			if ss_emp:
				social_security_wages += ss_emp / 0.062
				# social_security_tax_withheld += ss_emp

		# --- Medicare Wages & Tips ---
		if slip.custom_mc_taxable_wages and slip.custom_mc_taxable_wages > 0:
			medicare_wages_and_tips += slip.custom_mc_taxable_wages
		else:
			mc_emp = sum(
				d.amount for d in salary_slip_doc.deductions if d.salary_component == "Medicare Tax EE"
			)
			if mc_emp:
				medicare_wages_and_tips += mc_emp / 0.0145
				# medicare_tax_withheld += mc_emp

		# --- Federal income tax withheld ---
		for deduction in salary_slip_doc.deductions:
			component = frappe.get_cached_doc("Salary Component", deduction.salary_component)
			if component.custom_federal_income_tax_and_additional_withholdings:
				total_federal_income_tax_withheld += deduction.amount

			if component.name == "Social Security Tax - Employee":
				social_security_tax_withheld += deduction.amount

			if component.name == "Medicare Tax EE":
				medicare_tax_withheld += deduction.amount

	number_of_w2_forms = frappe.db.count(
		"W2 Form Details",
		filters={"docstatus": 1, "year_start_date": ["between", [year_start_date, year_end_date]]},
	)

	return {
		"wages_tips_other_compensation": wages_tips_other_compensation,
		"total_federal_income_tax_withheld": total_federal_income_tax_withheld,
		"social_security_tax_withheld": social_security_tax_withheld,
		"medicare_tax_withheld": medicare_tax_withheld,
		"number_of_w2_forms": number_of_w2_forms,
		"social_security_wages": social_security_wages,
		"medicare_wages_and_tips": medicare_wages_and_tips,
	}


@frappe.whitelist()
def fetch_address_details(is_your_company_address, link_doctype, link_name):
	address = frappe.db.sql(
		"""
			SELECT a.address_line1, a.address_line2, a.city, a.state, a.country, a.pincode, a.email_id,a.phone, a.fax
			FROM `tabAddress` a
			JOIN `tabDynamic Link` l ON l.parent = a.name
			WHERE a.is_your_company_address = 1
			  AND l.link_doctype = 'Company'
			  AND l.link_name = %(employer_name)s
		""",
		{"employer_name": link_name},
		as_dict=1,
	)

	for add in address:
		if add:
			address_line1 = add.get("address_line1") or ""
			address_line2 = add.get("address_line2") or ""
			city = add.get("city") or ""
			state = add.get("state") or ""
			country = add.get("country") or ""
			pincode = add.get("pincode") or ""
			email_id = add.get("email_id") or ""
			phone = add.get("phone") or ""
			fax = add.get("fax") or ""

			complete_address = ", ".join(
				filter(None, [address_line1, address_line2, city, state, country, pincode])
			)
			return {
				"complete_address": complete_address,
				"address_line1": address_line1,
				"address_line2": address_line2,
				"city": city,
				"state": state,
				"country": country,
				"pincode": pincode,
				"email_id": email_id,
				"phone": phone,
				"fax": fax,
			}
	return {
		"complete_address": "",
		"address_line1": "",
		"address_line2": "",
		"city": "",
		"state": "",
		"country": "",
		"pincode": "",
		"email_id": "",
		"phone": "",
	}


@frappe.whitelist()
def get_global_defaults_values(doctype):
	global_defaults_doc = frappe.get_doc("Global Defaults", doctype)
	company = global_defaults_doc.default_company
	return {"company": company}
