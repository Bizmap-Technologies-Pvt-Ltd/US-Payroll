import json
import os
from pathlib import Path

import frappe
from frappe.utils import getdate
from erpnext.accounts.utils import get_fiscal_year


def setup_wizard_complete(args=None):  # nosemgrep: overusing-args - framework hook signature
	company = frappe.defaults.get_global_default("company")

	# # Load JSON file
	# path = os.path.join(frappe.get_app_path("us_payroll"), "payroll", "data", "salary_components.json")
	# with open(path) as f:
	# 	components = json.load(f)

	file_path = Path(frappe.get_app_path("us_payroll")) / "payroll" / "data" / "salary_components.json"

	with file_path.open("r", encoding="utf-8") as f:
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

		##create income tax slabs
		create_income_tax_slabs()



def create_income_tax_slabs():
	"""Create Income Tax Slabs during setup with custom checkboxes, currency, and effective_from."""

	# Get current fiscal year start date
	today = getdate()
	fiscal_year, fiscal_year_start, fiscal_year_end = get_fiscal_year(today)
	effective_from = fiscal_year_start

	tax_slabs = [
		{
			"doctype": "Income Tax Slab",
			"name": "Single or Married Filing Separately",
			"currency": "USD",
			"effective_from": effective_from,
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Married Filing Jointly",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_married_filing_jointly": 1,
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Head of Household",
			"currency": "USD",
			"effective_from": effective_from,
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Single or Married filing separately with Form W-4",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_more_than_one_job": 1,
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Married filing jointly with Form W-4",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_married_filing_jointly": 1,
			"custom_more_than_one_job": 1,
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Head of Household with Form W4",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_more_than_one_job": 1,
		},
	]

	for slab in tax_slabs:
		if not frappe.db.exists("Income Tax Slab", {"name": slab["name"]}):
			doc = frappe.get_doc(slab)
			doc.insert(ignore_permissions=True, ignore_mandatory=True)

	frappe.db.commit()