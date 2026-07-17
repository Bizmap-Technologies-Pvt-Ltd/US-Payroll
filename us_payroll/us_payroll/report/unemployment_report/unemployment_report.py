# Copyright (c) 2025, bizmap and contributors
# For license information, please see license.txt

import calendar
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.jinja import get_jenv
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx


def execute(filters=None):
	if not filters:
		return [], []

	if not filters.get("quarter"):
		frappe.throw(_("Please select the Quarter."))

	columns = get_columns()

	querters = ["Quarter1", "Quarter2", "Quarter3", "Quarter4"]
	all_data = []
	qtr_mapper = {"Quarter1": 1, "Quarter2": 2, "Quarter3": 3, "Quarter4": 4}
	selected_quarter = qtr_mapper[filters.get("quarter")]

	for querter in querters:
		temp_filters = filters.copy()  # Create a copy
		temp_filters["quarter"] = querter
		data = get_data(temp_filters)
		all_data.extend(data)

	# Group by employee_id
	grouped_data = defaultdict(list)

	for row in all_data:
		grouped_data[row["employee_id"]].append(row)

	grouped_data = dict(grouped_data)
	for _emp_id, records in grouped_data.items():
		threshold_taxable_wage = 9000

		for record in records:
			reportable = record["reportable_wages"]

			record["taxable_wages"] = 0
			record["excess_wages"] = 0

			if threshold_taxable_wage > 0:
				if reportable <= threshold_taxable_wage:
					record["taxable_wages"] = reportable
					record["excess_wages"] = 0
					threshold_taxable_wage -= reportable
				else:
					record["taxable_wages"] = threshold_taxable_wage
					record["excess_wages"] = reportable - threshold_taxable_wage
					threshold_taxable_wage = 0
			else:
				record["taxable_wages"] = 0
				record["excess_wages"] = reportable

			record["contribution"] = round(0.013 * record["taxable_wages"], 2)

	all_data = [row for row in all_data if selected_quarter == row["quarter"]]

	# Get counts for each month (1-12) for the selected quarter only
	# month_employee_count = {i: 0 for i in range(1, 13)}

	quarter_to_months = {
		"Quarter1": [1, 2, 3],
		"Quarter2": [4, 5, 6],
		"Quarter3": [7, 8, 9],
		"Quarter4": [10, 11, 12],
	}

	selected_months = quarter_to_months[filters.get("quarter")]
	selected_year = int(filters.get("year"))

	salary_slips = frappe.db.sql(
		"""
		SELECT
			MONTH(cst.posting_date) AS month,
			cst.employee,
			cst.posting_date,
			emp.gender
		FROM `tabSalary Slip` cst
		JOIN `tabEmployee` emp
			ON cst.employee = emp.name
		WHERE YEAR(cst.posting_date) = %(year)s
		AND MONTH(cst.posting_date) IN %(months)s
		AND cst.docstatus != 2
		GROUP BY
			MONTH(cst.posting_date),
			cst.employee,
			emp.gender
	""",
		{"year": selected_year, "months": tuple(selected_months)},
		as_dict=True,
	)

	month_gender_counts = defaultdict(lambda: {"male": 0, "female": 0})

	for slip in salary_slips:
		posting_date = slip["posting_date"]
		gender = slip["gender"].strip().lower()

		month_year = posting_date.strftime("%Y-%m")

		if gender == "male":
			month_gender_counts[month_year]["male"] += 1
		elif gender == "female":
			month_gender_counts[month_year]["female"] += 1

	print_data = []
	for month_year, counts in sorted(month_gender_counts.items()):
		year, month = month_year.split("-")

		month_name = datetime.strptime(month, "%m").strftime("%B")

		print_data.append(
			{
				"month": month_name,
				"year": year,
				"male": counts["male"],
				"female": counts["female"],
				"total": counts["male"] + counts["female"],
			}
		)

	for record in all_data:
		record["print_data"] = print_data

	return columns, all_data


def get_data(filters):
	quarter_to_months = {
		"Quarter1": [1, 2, 3],
		"Quarter2": [4, 5, 6],
		"Quarter3": [7, 8, 9],
		"Quarter4": [10, 11, 12],
	}

	selected_year = int(filters.get("year"))
	selected_quarter = filters.get("quarter")

	if not selected_quarter or selected_quarter not in quarter_to_months:
		frappe.throw(_("Please select a valid quarter."))

	selected_months = quarter_to_months[selected_quarter]

	data = frappe.db.sql(
		"""
		SELECT
			pe.name AS payroll_entry,
			ped.employee,
			ped.employee_name,
			emp.department,
			emp.custom_nomasked_social_security_number,
			emp.gender,
			emp.first_name,
			emp.middle_name,
			emp.last_name,
			cst.posting_date,
			cst.gross_pay AS gross_pay,
			cst.name AS salary_slip,
			sd.salary_component,
			sd.amount AS salary_component_amount,
			-- ct.cost_center_name as custom_department_name,
			CEIL(MONTH(pe.posting_date)/3) AS quarter

		FROM
			`tabPayroll Entry` pe
		JOIN
			`tabPayroll Employee Detail` ped ON ped.parent = pe.name
		LEFT JOIN
			`tabEmployee` emp ON emp.name = ped.employee
		LEFT JOIN
			`tabSalary Slip` cst ON cst.employee = ped.employee AND cst.payroll_entry = pe.name
		LEFT JOIN
			`tabSalary Detail` sd ON sd.parent = cst.name
		LEFT JOIN
			`tabCost Center` ct ON ct.name = emp.department

		WHERE
			YEAR(pe.posting_date) = %(year)s
			AND MONTH(pe.posting_date) IN %(months)s
			AND MONTH(cst.posting_date) IN %(months)s
			AND cst.docstatus != 2
	""",
		{"year": selected_year, "months": tuple(selected_months)},
		as_dict=True,
	)

	# Grouping by salary slip
	grouped = {}
	for row in data:
		raw_ssn = str(row.get("custom_nomasked_social_security_number", ""))

		if len(raw_ssn) == 9 and raw_ssn.isdigit():
			formatted_ssn = f"{raw_ssn[:3]}-{raw_ssn[3:5]}-{raw_ssn[5:]}"
		else:
			formatted_ssn = raw_ssn

		slip = row["salary_slip"]
		if slip not in grouped:
			grouped[slip] = {
				"salary_slip": slip,
				"quarter": row["quarter"],
				"employee_id": row["employee"],
				"employee": row["employee_name"],
				"first_name": row["first_name"],
				"middle_name": row["middle_name"],
				"last_name": row["last_name"],
				"payroll_entry": row["payroll_entry"],
				"department": row["department"],
				"custom_nomasked_social_security_number": formatted_ssn,
				"gender": row["gender"],
				"reportable_wages": row["gross_pay"],  # Set once per slip
				"posting_date": row["posting_date"],
			}

	result = list(grouped.values())

	# Grouping by Employee
	grouped = {}
	for row in result:
		emp_ssn = str(row.get("custom_nomasked_social_security_number", ""))

		if len(emp_ssn) == 9 and emp_ssn.isdigit():
			emp_formatted_ssn = f"{emp_ssn[:3]}-{emp_ssn[3:5]}-{emp_ssn[5:]}"
		else:
			emp_formatted_ssn = emp_ssn

		employee = row["employee"]
		if employee not in grouped:
			grouped[employee] = {
				"salary_slip": row["salary_slip"],
				"quarter": row["quarter"],
				"employee_id": row["employee_id"],
				"employee": row["employee"],
				"first_name": row["first_name"],
				"middle_name": row["middle_name"],
				"last_name": row["last_name"],
				"payroll_entry": row["payroll_entry"],
				"department": row["department"],
				"custom_nomasked_social_security_number": emp_formatted_ssn,
				"gender": row["gender"],
				"reportable_wages": 0.0,  # Set once per slip
				"posting_date": row["posting_date"],
			}

		grouped[employee]["reportable_wages"] += row["reportable_wages"]

	result = list(grouped.values())

	return result


def get_columns():
	columns = [
		{
			"label": _("Payroll Entry"),
			"fieldname": "payroll_entry",
			"fieldtype": "Link",
			"options": "Payroll Entry",
			"width": 150,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"align": "center",
			"width": 150,
		},
		{
			"label": _("Social Security Number"),
			"fieldname": "custom_nomasked_social_security_number",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Reportable Wages"),
			"fieldname": "reportable_wages",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Excess Wages"),
			"fieldname": "excess_wages",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Taxable Wages"),
			"fieldname": "taxable_wages",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Contribution"),
			"fieldname": "contribution",
			"fieldtype": "Currency",
			"width": 150,
		},
	]

	return columns


@frappe.whitelist()
def get_print(report_data: str):
	report_data = json.loads(report_data)
	report_data = {"filter": report_data["filter"], "data": report_data}

	return generate_pdf(report_data)


@frappe.whitelist()
def generate_pdf(data: dict[str, Any]):
	filters = data.get("filter")
	quarter_to_months = {
		"Quarter1": [1, 2, 3],
		"Quarter2": [4, 5, 6],
		"Quarter3": [7, 8, 9],
		"Quarter4": [10, 11, 12],
	}

	selected_quarter = filters.get("quarter")
	selected_year = int(filters.get("year"))

	if not selected_quarter or selected_quarter not in quarter_to_months:
		frappe.throw(_("Please select a valid quarter."))

	months = quarter_to_months[selected_quarter]
	start_date = datetime(selected_year, months[0], 1)
	last_day = calendar.monthrange(selected_year, months[-1])[1]
	end_date = datetime(selected_year, months[-1], last_day)

	quarter_period_range = start_date.strftime("%m/%d/%Y") + " - " + end_date.strftime("%m/%d/%Y")

	month_year = f"{selected_quarter} {selected_year}"

	letterhead_image = frappe.db.get_value("Letter Head", {"is_default": True}, "image")
	site_url = frappe.utils.get_url()
	if letterhead_image and not letterhead_image.startswith("http"):
		letterhead_image = site_url + letterhead_image

	data = data.get("data")["data"]
	print_data = data[0]["print_data"]

	month_lookup = {}

	for row in print_data:
		month_lookup[row["month"]] = row

	quarter_month_names = {
		"Quarter1": ["January", "February", "March"],
		"Quarter2": ["April", "May", "June"],
		"Quarter3": ["July", "August", "September"],
		"Quarter4": ["October", "November", "December"],
	}

	months = quarter_month_names[selected_quarter]

	employee_counts = {
		"first_month": {
			"total": month_lookup.get(months[0], {}).get("total", 0),
			"male": month_lookup.get(months[0], {}).get("male", 0),
			"female": month_lookup.get(months[0], {}).get("female", 0),
			"unknown": 0,
		},
		"second_month": {
			"total": month_lookup.get(months[1], {}).get("total", 0),
			"male": month_lookup.get(months[1], {}).get("male", 0),
			"female": month_lookup.get(months[1], {}).get("female", 0),
			"unknown": 0,
		},
		"third_month": {
			"total": month_lookup.get(months[2], {}).get("total", 0),
			"male": month_lookup.get(months[2], {}).get("male", 0),
			"female": month_lookup.get(months[2], {}).get("female", 0),
			"unknown": 0,
		},
	}

	department_data, department_grand_totals = get_department_summary(data)

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M:%S %p")
	company_name = frappe.defaults.get_global_default("company").replace("City of ", "")
	company_name = f"City of {company_name}"

	# Template path is hardcoded and bundled with the app, not user-controlled.
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	template = frappe.get_template(
		"us_payroll/us_payroll/report/unemployment_report/unemployment_report.html"
	)

	html = template.render(
		{
			"data": data,
			"department_data": department_data,
			"grand_totals": department_grand_totals,
			"filter": filters,
			"current_datetime": formatted_datetime,
			"letterhead_image": letterhead_image,
			"company_name": company_name,
			"start_date": start_date,
			"end_date": end_date,
			"month_year": month_year,
			"quarter_period_range": quarter_period_range,
			"print_data": print_data,
			"employee_counts": employee_counts,
		}
	)

	options = {
		"page-width": "2000px",
		"page-height": "1500px",
		"orientation": "Landscape",
		"margin-right": "20mm",
		"margin-left": "20mm",
	}

	pdf_file = get_pdf(html, options=options)
	return {
		"data": data,
		"department_data": department_data,
		"grand_totals": department_grand_totals,
		"html": html,
		"pdf_file": pdf_file,
	}


def get_department_summary(data):
	department_summary = defaultdict(
		lambda: {
			"department_code": "",
			"employee_count": 0,
			"reportable_wages": 0.0,
			"excess_wages": 0.0,
			"taxable_wages": 0.0,
			"contribution": 0.0,
			"employees": [],
		}
	)

	for row in data:
		department_code = row.get("department") or "Unknown"

		if department_code == "Unknown":
			continue

		department_code_name = f"{department_code}"
		summary = department_summary[department_code_name]

		if not summary["department_code"]:
			summary["department_code"] = department_code

		summary["employee_count"] += 1
		summary["reportable_wages"] += float(row.get("reportable_wages") or 0)
		summary["excess_wages"] += float(row.get("excess_wages") or 0)
		summary["taxable_wages"] += float(row.get("taxable_wages") or 0)
		summary["contribution"] += float(row.get("contribution") or 0)

		summary["employees"].append(
			{
				"employee_id": row.get("employee_id"),
				"employee": row.get("employee"),
				"custom_nomasked_social_security_number": row.get("custom_nomasked_social_security_number"),
				"reportable_wages": float(row.get("reportable_wages") or 0),
				"excess_wages": float(row.get("excess_wages") or 0),
				"taxable_wages": float(row.get("taxable_wages") or 0),
				"contribution": float(row.get("contribution") or 0),
				"department_code_name": department_code_name,
			}
		)

	department_list = list(department_summary.values())
	department_list.sort(
		key=lambda x: (x["department_code"].zfill(5)) if x["department_code"].isdigit() else "99999"
	)

	grand_totals = {
		"employee_count": sum(d["employee_count"] for d in department_list),
		"reportable_wages": sum(d["reportable_wages"] for d in department_list),
		"excess_wages": sum(d["excess_wages"] for d in department_list),
		"taxable_wages": sum(d["taxable_wages"] for d in department_list),
		"contribution": sum(d["contribution"] for d in department_list),
	}

	return department_list, grand_totals


@frappe.whitelist()
def download_excel(filters: str):
	filters = frappe._dict(json.loads(filters))
	_columns, data = execute(filters)

	xlsx_data = []
	for row in data:
		first_name = row.get("first_name")
		middle_name = row.get("middle_name")

		first_initial = first_name[0] if first_name else ""
		middle_initial = middle_name[0] if middle_name else ""
		xlsx_data.append(
			[
				row.get("custom_nomasked_social_security_number", "").replace("-", ""),
				first_initial,
				middle_initial,
				row.get("last_name", ""),
				row.get("taxable_wages", 0.0),
			]
		)

	file_name = "Unemployment_Report.xlsx"
	xlsx_file = make_xlsx(xlsx_data, file_name)

	saved_file = save_file(file_name, xlsx_file.getvalue(), "Report", "Unemployment Report", is_private=1)

	return {"file_url": saved_file.file_url}
