# Copyright (c) 2025, bizmap and contributors
# For license information, please see license.txt

import calendar
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf


def execute(filters=None):
	if not filters:
		return [], []

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	month_name_to_number = {
		"January": 1,
		"February": 2,
		"March": 3,
		"April": 4,
		"May": 5,
		"June": 6,
		"July": 7,
		"August": 8,
		"September": 9,
		"October": 10,
		"November": 11,
		"December": 12,
	}

	selected_year = int(filters.get("year"))
	selected_month_name = filters.get("month")
	selected_month = month_name_to_number.get(selected_month_name)

	if not selected_month:
		frappe.throw(_("Please select a valid month."))

	# # Calculate previous month and year
	# if selected_month == 1:
	# 	prev_month = 12
	# 	prev_year = selected_year - 1
	# else:
	# 	prev_month = selected_month - 1
	# 	prev_year = selected_year

	# # Get first and last day of previous month
	# start_date = datetime(selected_year, selected_month, 1)
	# last_day = calendar.monthrange(selected_year, selected_month)[1]
	# end_date = datetime(selected_year, selected_month, last_day)

	data = frappe.db.sql(
		"""
			SELECT
				pe.name AS payroll_entry,
				ped.employee,
				ped.employee_name,
				emp.department,
				emp.custom_nomasked_social_security_number,
				emp.first_name,
				emp.middle_name,
				emp.last_name,
				cst.gross_pay AS gross_pay,
				cst.name AS salary_slip,
				sd.salary_component,
				sd.amount AS salary_component_amount,
				(CASE
				WHEN sd.salary_component = 'TMRS (Employee)' THEN sd.amount
				ELSE 0
			END) AS tmrs_employee_total,
			(CASE
				WHEN sd.salary_component = 'TMRS (Employer)' THEN sd.amount
				ELSE 0
			END) AS tmrs_employer_total,
			dept.name as department

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
				`tabDepartment` dept ON dept.name = emp.department

			WHERE
				YEAR(pe.posting_date) = %(year)s
				AND MONTH(pe.posting_date) = %(selected_month)s
				AND MONTH(cst.posting_date) = %(selected_month)s
				AND cst.docstatus = 1
				AND sd.salary_component IN ('TMRS (Employee)', 'TMRS (Employer)')
		""",
		{"selected_month": selected_month, "year": selected_year},
		as_dict=True,
	)

	# Grouping by salary slip
	grouped = {}
	for row in data:
		raw_ssn = str(row.get("custom_nomasked_social_security_number", ""))
		if len(raw_ssn) == 9 and raw_ssn.isdigit():
			formatted_ssn = f"{raw_ssn[:3]}-{raw_ssn[3:5]}-{raw_ssn[5:]}"
		else:
			formatted_ssn = raw_ssn  # fallback (leave it unchanged if not valid)

		slip = row["salary_slip"]
		if slip not in grouped:
			grouped[slip] = {
				"salary_slip": slip,
				"employee": row["employee_name"],
				"first_name": row["first_name"],
				"middle_name": row["middle_name"],
				"last_name": row["last_name"],
				"payroll_entry": row["payroll_entry"],
				"department": row["department"],
				"custom_nomasked_social_security_number": formatted_ssn,
				"gross_pay": row["gross_pay"],  # Set once per slip
				"tmrs_employee_total": 0.0,
				"tmrs_employer_total": 0.0,
			}

		if "Employee" in row["salary_component"]:
			grouped[slip]["tmrs_employee_total"] += row["salary_component_amount"]
		elif "Employer" in row["salary_component"]:
			grouped[slip]["tmrs_employer_total"] += row["salary_component_amount"]

	result = list(grouped.values())

	for row in result:
		row["total_contribution"] = round(row["tmrs_employee_total"] + row["tmrs_employer_total"], 2)

	# Grouping by Employee
	grouped = {}
	for row in result:
		emp_ssn = str(row.get("custom_nomasked_social_security_number", ""))
		if len(emp_ssn) == 9 and emp_ssn.isdigit():
			emp_formatted_ssn = f"{emp_ssn[:3]}-{emp_ssn[3:5]}-{emp_ssn[5:]}"
		else:
			emp_formatted_ssn = emp_ssn  # fallback (leave it unchanged if not valid)

		employee = row["employee"]
		if employee not in grouped:
			grouped[employee] = {
				"salary_slip": slip,
				"employee": row["employee"],
				"first_name": row["first_name"],
				"middle_name": row["middle_name"],
				"last_name": row["last_name"],
				"payroll_entry": row["payroll_entry"],
				"department": row["department"],
				"custom_nomasked_social_security_number": emp_formatted_ssn,
				"gross_pay": 0.0,  # Set once per slip
				"tmrs_employee_total": 0.0,
				"tmrs_employer_total": 0.0,
			}

		grouped[employee]["gross_pay"] += row["gross_pay"]
		grouped[employee]["tmrs_employee_total"] += row["tmrs_employee_total"]
		grouped[employee]["tmrs_employer_total"] += row["tmrs_employer_total"]

	result = list(grouped.values())
	for row in result:
		row["total_contribution"] = round(row["tmrs_employee_total"] + row["tmrs_employer_total"], 2)

	return result


def get_columns():
	columns = []
	"payroll_entry"
	columns = [
		{
			"label": _("Employee"),
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
			"label": _("Subject Wages"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Employee Amount"),
			"fieldname": "tmrs_employee_total",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Employer Amount"),
			"fieldname": "tmrs_employer_total",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Total Contribution"),
			"fieldname": "total_contribution",
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
	month_name_to_number = {
		"January": 1,
		"February": 2,
		"March": 3,
		"April": 4,
		"May": 5,
		"June": 6,
		"July": 7,
		"August": 8,
		"September": 9,
		"October": 10,
		"November": 11,
		"December": 12,
	}

	selected_year = int(filters.get("year"))
	selected_month_name = filters.get("month")
	selected_month = month_name_to_number.get(selected_month_name)

	month_year = f"{selected_month_name} {selected_year}"

	if not selected_month:
		frappe.throw(_("Please select a valid month."))

	# Get first and last day of previous month
	start_date = datetime(selected_year, selected_month, 1)
	last_day = calendar.monthrange(selected_year, selected_month)[1]
	end_date = datetime(selected_year, selected_month, last_day)

	formatted_start_date = start_date.strftime("%m/%d/%Y")
	formatted_end_date = end_date.strftime("%m/%d/%Y")

	formatted_start_end_date = f"{formatted_start_date} - {formatted_end_date}"

	template_path = "us_payroll/us_payroll/report/tmrs_report/tmrs_report.html"

	letterhead_image = frappe.db.get_value("Letter Head", {"is_default": True}, "image")

	data = data.get("data")["data"]

	department_data, department_grand_totals = get_department_summary(data)

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M%p").lower()

	company_name = frappe.defaults.get_global_default("company").replace("City of ", "")
	company_name = f"City of {company_name}"

	html = frappe.render_template(  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		template_path,
		{
			"data": data,
			"department_data": department_data,
			"department_grand_totals": department_grand_totals,
			"filter": filters,
			"current_datetime": formatted_datetime,
			"letterhead_image": letterhead_image,
			"company_name": company_name,
			"start_date": start_date,
			"end_date": end_date,
			"formatted_start_end_date": formatted_start_end_date,
			"month_year": month_year,
		},
	)

	options = {
		"page-width": "2000px",
		"page-height": "1500px",
		"orientation": "Landscape",
		"margin-right": "20mm",
		"margin-left": "20mm",
	}

	pdf_file = get_pdf(html, options=options)
	return {"data": data, "department_data": department_data, "html": html, "pdf_file": pdf_file}


def get_department_summary(data):
	department_summary = defaultdict(
		lambda: {
			"department_code": "",
			"department_description": "",
			"employee_count": 0,
			"subject_wages": 0.0,
			"employee_amount": 0.0,
			"employer_amount": 0.0,
			"total_contribution": 0.0,
		}
	)

	data = [row for row in data if row.get("employee") != "Total"]
	for row in data:
		department = row.get("department") or "Unknown Department"

		if " " in department:
			department_code, department_description = department.split(" ", 1)
		else:
			department_code = department
			department_description = department

		summary = department_summary[department]
		summary["department_code"] = department_code
		summary["department_description"] = department_description
		summary["employee_count"] += 1
		summary["subject_wages"] += float(row.get("gross_pay") or 0)
		summary["employee_amount"] += float(row.get("tmrs_employee_total") or 0)
		summary["employer_amount"] += float(row.get("tmrs_employer_total") or 0)
		summary["total_contribution"] += float(row.get("total_contribution") or 0)

	department_list = list(department_summary.values())
	department_list.sort(
		key=lambda x: (x["department_code"].zfill(5)) if x["department_code"].isdigit() else "99999"
	)
	grand_totals = {
		"employee_count": sum(d["employee_count"] for d in department_list),
		"subject_wages": sum(d["subject_wages"] for d in department_list),
		"employee_amount": sum(d["employee_amount"] for d in department_list),
		"employer_amount": sum(d["employer_amount"] for d in department_list),
		"total_contribution": sum(d["total_contribution"] for d in department_list),
	}
	return department_list, grand_totals
