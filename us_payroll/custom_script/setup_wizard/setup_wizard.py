import json
import os
from pathlib import Path

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import getdate


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
	"""Create Income Tax Slabs during setup."""

	today = getdate()
	_fiscal_year, fiscal_year_start, _fiscal_year_end = get_fiscal_year(today)
	effective_from = fiscal_year_start

	tax_slabs = [
		{
			"doctype": "Income Tax Slab",
			"name": "Single or Married Filing Separately",
			"currency": "USD",
			"effective_from": effective_from,
			"slabs": [
				{"from_amount": 0, "to_amount": 7500, "percent_deduction": 0},
				{"from_amount": 7501, "to_amount": 19000, "percent_deduction": 10},
				{"from_amount": 19001, "to_amount": 57900, "percent_deduction": 12},
				{"from_amount": 57901, "to_amount": 113200, "percent_deduction": 22},
				{"from_amount": 113201, "to_amount": 209275, "percent_deduction": 24},
				{"from_amount": 209276, "to_amount": 263725, "percent_deduction": 32},
				{"from_amount": 263726, "to_amount": 648100, "percent_deduction": 35},
				{"from_amount": 648101, "to_amount": 900000, "percent_deduction": 37},
			],
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Married Filing Jointly",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_married_filing_jointly": 1,
			"slabs": [
				{"from_amount": 19301, "to_amount": 44100, "percent_deduction": 10},
				{"from_amount": 44101, "to_amount": 120100, "percent_deduction": 12},
				{"from_amount": 120101, "to_amount": 230700, "percent_deduction": 22},
				{"from_amount": 230701, "to_amount": 422850, "percent_deduction": 24},
				{"from_amount": 422851, "to_amount": 531750, "percent_deduction": 32},
				{"from_amount": 531751, "to_amount": 788000, "percent_deduction": 35},
				{"from_amount": 788001, "to_amount": 1000000, "percent_deduction": 37},
			],
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Head of Household",
			"currency": "USD",
			"effective_from": effective_from,
			"slabs": [
				{"from_amount": 0, "to_amount": 15550, "percent_deduction": 0},
				{"from_amount": 15551, "to_amount": 33250, "percent_deduction": 10},
				{"from_amount": 33251, "to_amount": 83000, "percent_deduction": 12},
				{"from_amount": 83001, "to_amount": 121250, "percent_deduction": 22},
				{"from_amount": 121251, "to_amount": 217300, "percent_deduction": 24},
				{"from_amount": 217301, "to_amount": 271750, "percent_deduction": 32},
				{"from_amount": 271751, "to_amount": 656150, "percent_deduction": 35},
				{"from_amount": 656151, "to_amount": 900000, "percent_deduction": 37},
			],
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Single or Married filing separately with Form W-4",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_more_than_one_job": 1,
			"slabs": [
				{"from_amount": 0, "to_amount": 8050, "percent_deduction": 0},
				{"from_amount": 8051, "to_amount": 14250, "percent_deduction": 10},
				{"from_amount": 14251, "to_amount": 33250, "percent_deduction": 12},
				{"from_amount": 33251, "to_amount": 60900, "percent_deduction": 22},
				{"from_amount": 60901, "to_amount": 108938, "percent_deduction": 24},
				{"from_amount": 108939, "to_amount": 136163, "percent_deduction": 32},
				{"from_amount": 136164, "to_amount": 328350, "percent_deduction": 35},
				{"from_amount": 328351, "to_amount": 900000, "percent_deduction": 37},
			],
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Married filing jointly with Form W-4",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_married_filing_jointly": 1,
			"custom_more_than_one_job": 1,
			"slabs": [
				{"from_amount": 16101, "to_amount": 28500, "percent_deduction": 10},
				{"from_amount": 28501, "to_amount": 66500, "percent_deduction": 12},
				{"from_amount": 66501, "to_amount": 121800, "percent_deduction": 22},
				{"from_amount": 121801, "to_amount": 217875, "percent_deduction": 24},
				{"from_amount": 217876, "to_amount": 272325, "percent_deduction": 32},
				{"from_amount": 272326, "to_amount": 400450, "percent_deduction": 35},
				{"from_amount": 400451, "to_amount": 10000000, "percent_deduction": 37},
			],
		},
		{
			"doctype": "Income Tax Slab",
			"name": "Head of Household with Form W4",
			"currency": "USD",
			"effective_from": effective_from,
			"custom_more_than_one_job": 1,
			"slabs": [
				{"from_amount": 0, "to_amount": 12075, "percent_deduction": 0},
				{"from_amount": 12076, "to_amount": 20925, "percent_deduction": 10},
				{"from_amount": 20926, "to_amount": 45800, "percent_deduction": 12},
				{"from_amount": 45801, "to_amount": 64925, "percent_deduction": 22},
				{"from_amount": 64926, "to_amount": 112950, "percent_deduction": 24},
				{"from_amount": 112951, "to_amount": 140175, "percent_deduction": 32},
				{"from_amount": 140176, "to_amount": 332375, "percent_deduction": 35},
				{"from_amount": 332376, "to_amount": 900000, "percent_deduction": 37},
			],
		},
	]

	for slab in tax_slabs:
		if not frappe.db.exists("Income Tax Slab", slab["name"]):
			slab_rows = slab.pop("slabs", [])

			doc = frappe.get_doc(slab)

			for row in slab_rows:
				doc.append("slabs", row)

			doc.insert(ignore_permissions=True, ignore_mandatory=True)

	frappe.db.commit()
