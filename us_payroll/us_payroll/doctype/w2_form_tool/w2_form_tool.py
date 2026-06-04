# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class W2FormTool(Document):
	pass


@frappe.whitelist()
def get_employees(doc):
	doc = frappe.parse_json(doc)

	if not doc.get("year_start_date") or not doc.get("year_end_date"):
		frappe.throw("Year Start Date and Year End Date are required")

	salary_slips = frappe.get_all(
		"Salary Slip",
		filters={"posting_date": ["between", [doc["year_start_date"], doc["year_end_date"]]], "docstatus": 1},
		fields=[
			"name",
			"employee",
			"employee_name",
			"gross_pay",
			"custom_taxable_wages",
			"custom_total_non_taxable_earnings",
			"custom_ss_taxable_wages",
			"custom_mc_taxable_wages",
		],
	)

	employee_map = {}
	for slip in salary_slips:
		if slip.employee not in employee_map:
			emp = frappe.get_doc("Employee", slip.employee)

			employee_map[slip.employee] = {
				"employee": slip.employee,
				"control_number": emp.name,
				"employee_name": slip.employee_name,
				"first_name": emp.first_name,
				"last_name": emp.last_name,
				"social_security_number": emp.custom_nomasked_social_security_number,
				"address": (
					f"{emp.employee_name}\n"
					f"{emp.custom_address_line_1 or ''}\n"
					f"{emp.custom_address_line_2 or ''}\n"
					f"{emp.custom_city or ''} "
					f"{emp.custom_stateprovince or ''} "
					f"{emp.custom_zip_postal_code or ''}"
				),
				"wages_tips_other_compensation": 0,
				"federal_income_tax_withheld": 0,
				"social_security_tax_withheld": 0,
				"medicare_tax_withheld": 0,
				"tmrs": 0,
				"medical_insurance": 0,
				"social_security_wages": 0,
				"medicare_wages_and_tips": 0,
				"retirement_plan": False,
			}

		# --- Wages, tips, other compensation ---
		if slip.custom_taxable_wages:
			employee_map[slip.employee]["wages_tips_other_compensation"] += slip.custom_taxable_wages
		else:
			non_taxable = slip.custom_total_non_taxable_earnings or 0
			wages = (slip.gross_pay or 0) - non_taxable
			employee_map[slip.employee]["wages_tips_other_compensation"] += wages

		slip_doc = frappe.get_doc("Salary Slip", slip.name)
		for d in slip_doc.deductions:
			comp = frappe.get_doc("Salary Component", d.salary_component)

			if comp.custom_federal_income_tax_and_additional_withholdings:
				employee_map[slip.employee]["federal_income_tax_withheld"] += d.amount

			if comp.name == "Social Security Tax - Employee":
				employee_map[slip.employee]["social_security_tax_withheld"] += d.amount

			if comp.name == "Medicare Tax EE":
				employee_map[slip.employee]["medicare_tax_withheld"] += d.amount

			if comp.name == "TMRS (Employee)":
				employee_map[slip.employee]["tmrs"] += d.amount
				employee_map[slip.employee]["retirement_plan"] = True

			if comp.name in ["TML-Medical (Pre-Tax)", "TML-Medical ER (Pre-Tax)"]:
				employee_map[slip.employee]["medical_insurance"] += d.amount

		# --- Social Security Wages ---
		if slip.custom_ss_taxable_wages and slip.custom_ss_taxable_wages > 0:
			employee_map[slip.employee]["social_security_wages"] += slip.custom_ss_taxable_wages
		else:
			ss_emp = sum(
				d.amount
				for d in slip_doc.deductions
				if d.salary_component == "Social Security Tax - Employee"
			)
			if ss_emp:
				employee_map[slip.employee]["social_security_wages"] += ss_emp / 0.062

		# --- Medicare Wages & Tips ---
		if slip.custom_mc_taxable_wages and slip.custom_mc_taxable_wages > 0:
			employee_map[slip.employee]["medicare_wages_and_tips"] += slip.custom_mc_taxable_wages
		else:
			mc_emp = sum(d.amount for d in slip_doc.deductions if d.salary_component == "Medicare Tax EE")
			if mc_emp:
				employee_map[slip.employee]["medicare_wages_and_tips"] += mc_emp / 0.0145

	return list(employee_map.values())


@frappe.whitelist()
def generate_w2_form_records(doc):
	doc = frappe.parse_json(doc)

	created = []
	skipped = []

	for row in doc.get("w2_form_details", []):
		if frappe.db.exists("W2 Form Details", {"employee": row["employee"], "year": doc["year"]}):
			skipped.append(
				{"employee": row["employee"], "employee_name": row["employee_name"], "year": doc["year"]}
			)
			continue

		company = frappe.defaults.get_global_default("company")
		employer_identification_number_ein = frappe.db.get_value("Company", company, "tax_id")
		company_address = get_company_address_text()

		w2 = frappe.new_doc("W2 Form Details")
		w2.employee = row["employee"]
		w2.control_number = row["control_number"]
		w2.employee_name = row["employee_name"]
		w2.first_name = row["first_name"]
		w2.last_name = row["last_name"]
		w2.social_security_number = row["social_security_number"]
		w2.address = row["address"]

		w2.year = doc["year"]
		w2.year_start_date = doc["year_start_date"]
		w2.year_end_date = doc["year_end_date"]

		w2.company_address = company_address
		w2.employer_identification_number_ein = employer_identification_number_ein

		w2.wages_tips_other_compensation = row["wages_tips_other_compensation"]
		w2.federal_income_tax_withheld = row["federal_income_tax_withheld"]
		w2.social_security_tax_withheld = row["social_security_tax_withheld"]
		w2.medicare_tax_withheld = row["medicare_tax_withheld"]
		w2.tmrs = row["tmrs"]
		w2.medical_insurance = row["medical_insurance"]
		w2.retirement_plan = row["retirement_plan"]
		w2.social_security_wages = row["social_security_wages"]
		w2.medicare_wages_and_tips = row["medicare_wages_and_tips"]

		w2.insert()
		w2.submit()

		created.append(
			{
				"name": w2.name,
				"employee": row["employee"],
				"employee_name": row["employee_name"],
				"year": doc["year"],
			}
		)

	return {"created": created, "skipped": skipped}


def get_company_address_text():
	address = frappe.db.get_value(
		"Address",
		{"is_your_company_address": 1},
		["address_line1", "address_line2", "city", "state", "pincode", "country"],
		as_dict=True,
	)

	if not address:
		return ""

	employer_address = (
		f"{address.address_line1 or ''}\n"
		f"{address.address_line2 or ''}\n"
		f"{address.city or ''}, {address.state or ''} {address.pincode or ''}\n"
		f"{address.country or ''}"
	)

	return employer_address
