import json
import os

import frappe


def setup_wizard_complete(args=None):
	company = frappe.defaults.get_global_default("company")
	abbr = frappe.db.get_value("Company", company, "abbr")

	# Load JSON file
	path = os.path.join(frappe.get_app_path("us_payroll"), "payroll", "data", "salary_components.json")
	with open(path) as f:
		components = json.load(f)

	# Create components only if missing
	for comp in components:
		if not frappe.db.exists("Salary Component", {"salary_component": comp["salary_component"]}):
			doc = frappe.get_doc(comp)
			doc.insert(ignore_permissions=True, ignore_mandatory=True)

	# Now create Salary Structure referencing those components
	if not frappe.db.exists("Salary Structure", {"name": "Standard Salary Template"}):
		structure_doc = frappe.get_doc(
			{
				"doctype": "Salary Structure",
				"name": "Standard Salary Template",
				"salary_structure_name": "Standard Salary Template",
				"company": company,
				"is_active": "Yes",
				"payroll_frequency": "Fortnightly",
				"currency": "USD",
				"earnings": [
					{"salary_component": "Hourly"},
					{"salary_component": "Overtime"},
					{"salary_component": "Salary"},
				],
				"deductions": [
					{"salary_component": "Dental"},
					{"salary_component": "FIT"},
					{"salary_component": "Social Security Tax - Employee"},
					{"salary_component": "Social Security Tax - Employer"},
					{"salary_component": "Medicare Tax EE"},
					{"salary_component": "Medicare Tax ER"},
					{"salary_component": "TMRS (Employee)"},
					{"salary_component": "TMRS (Employer)"},
				],
			}
		)
		structure_doc.insert(ignore_permissions=True, ignore_mandatory=True)
