# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import render_template
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf


class W2FormDetails(Document):
	pass


@frappe.whitelist()
def calculate_totals(doc):
	doc = json.loads(doc)
	# if not (doc.get("year_start_date") and doc.get("year_end_date")):
	# 	frappe.throw("Please make sure Year Start Date, and Year End Date are set.")

	employee = doc.get("employee")
	year_start_date = doc.get("year_start_date")
	year_end_date = doc.get("year_end_date")

	salary_slips = frappe.get_all(
		"Salary Slip",
		filters={
			"employee": employee,
			"posting_date": ["between", [year_start_date, year_end_date]],
			"docstatus": 1,
		},
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
	tmrs = 0.0
	medical_insurance = 0.0
	retirement_plan = False

	# Wage bases
	social_security_wages = 0.0
	medicare_wages_and_tips = 0.0

	for slip in salary_slips:
		salary_slip_doc = frappe.get_doc("Salary Slip", slip["name"])

		# --- Wages, tips, other compensation ---
		if slip.custom_taxable_wages:
			wages_tips_other_compensation += slip.custom_taxable_wages
		else:
			non_taxable = slip.custom_total_non_taxable_earnings or 0
			wages = (slip.gross_pay or 0) - non_taxable
			wages_tips_other_compensation += wages

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

		# --- Other deductions ---
		for deduction in salary_slip_doc.deductions:
			salary_component = frappe.get_doc("Salary Component", deduction.salary_component)

			if salary_component.custom_federal_income_tax_and_additional_withholdings:
				total_federal_income_tax_withheld += deduction.amount

			if salary_component.name == "TMRS (Employee)":
				tmrs += deduction.amount
				retirement_plan = True

			if salary_component.name in ["TML-Medical (Pre-Tax)", "TML-Medical ER (Pre-Tax)"]:
				medical_insurance += deduction.amount

			if salary_component.name == "Social Security Tax - Employee":
				social_security_tax_withheld += deduction.amount

			if salary_component.name == "Medicare Tax EE":
				medicare_tax_withheld += deduction.amount

	return {
		"total_gross_pay": wages_tips_other_compensation,
		"total_federal_income_tax_withheld": total_federal_income_tax_withheld,
		"social_security_tax_withheld": social_security_tax_withheld,
		"medicare_tax_withheld": medicare_tax_withheld,
		"social_security_wages": social_security_wages,
		"medicare_wages_and_tips": medicare_wages_and_tips,
		"tmrs": tmrs,
		"medical_insurance": medical_insurance,
		"retirement_plan": retirement_plan,
	}


@frappe.whitelist()
def bulk_w2_print(names):
	names = frappe.parse_json(names)
	if not names:
		frappe.throw("No records selected")

	docs = [frappe.get_doc("W2 Form Details", name) for name in names]
	html = render_template("us_payroll/us_payroll/doctype/w2_form_details/w2_bulk_print.html", {"docs": docs})

	# options = {
	# 	'margin-top': '14mm',
	# 	'margin-bottom': '0mm',
	# }
	# pdf = get_pdf(html, options=options)

	pdf = get_pdf(html)
	frappe.local.response.filename = "W2-Bulk.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"
