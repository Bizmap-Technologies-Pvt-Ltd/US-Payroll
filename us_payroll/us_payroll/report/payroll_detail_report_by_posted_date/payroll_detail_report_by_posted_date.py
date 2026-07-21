# Copyright (c) 2025, bizmap and contributors
# For license information, please see license.txt

import calendar
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils.jinja import get_jenv
from frappe.utils.pdf import get_pdf


def execute(filters=None):
	if not filters.get("from_date"):
		frappe.throw(_("Please select the from_date."))

	if not filters.get("to_date"):
		frappe.throw(_("Please select the to_date."))

	if not filters:
		return [], []

	columns = get_columns()
	all_data = get_data(filters)
	return columns, all_data


def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	department = filters.get("department")

	if not from_date or not to_date:
		frappe.throw(_("Please select both From Date and To Date."))

	department = department or ""

	data = frappe.db.sql(
		"""
		SELECT
			cst.payroll_entry AS payroll_entry,
			cst.employee,
			cst.employee_name,
			emp.first_name,
			emp.middle_name,
			emp.last_name,
			COALESCE(emp.custom_hourly_rate, 0) as rate,
			cst.name AS salary_slip,
			dept.name as department,
			COALESCE(SUM(cst.net_pay), 0) AS net_pay,
			COALESCE(SUM(cst.gross_pay), 0) AS gross_pay
		FROM `tabSalary Slip` cst
		LEFT JOIN `tabEmployee` emp ON emp.name = cst.employee
		LEFT JOIN `tabDepartment` dept ON dept.name = emp.department
		WHERE cst.posting_date BETWEEN %(from_date)s AND %(to_date)s
		  AND cst.docstatus = 1
		  AND (%(department)s = '' OR emp.department = %(department)s)
		GROUP BY cst.employee
	""",
		{"from_date": from_date, "to_date": to_date, "department": department},
		as_dict=True,
	)

	for row in data:
		row["rate"] = float(row.get("rate") or 0)
		row["total_net_pay"] = float(row.get("net_pay") or 0)
		row["total_gross_pay"] = float(row.get("gross_pay") or 0)

	return data


def get_columns():
	columns = [
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"align": "center",
			"width": 150,
		},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Float", "align": "center", "width": 150},
		{"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "width": 150},
		{"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Currency", "width": 150},
		# {'label': 'Total', 'fieldname': 'total_net_pay', 'fieldtype': 'Currency','width': 150},
	]

	return columns


@frappe.whitelist()
def get_print(report_data: str):
	report_data = json.loads(report_data)
	report_data = {"filter": report_data["filter"], "data": report_data}

	return generate_pdf(report_data)


@frappe.whitelist()
def generate_pdf(data: dict[str, Any]):
	filters = data.get("filter", {})

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not from_date or not to_date:
		frappe.throw(_("Please select both From Date and To Date."))

	from_date = datetime.strptime(from_date, "%Y-%m-%d")
	to_date = datetime.strptime(to_date, "%Y-%m-%d")
	formatted_from_date = from_date.strftime("%m/%d/%Y")
	formatted_to_date = to_date.strftime("%m/%d/%Y")
	formatted_date_range = f"{formatted_from_date} - {formatted_to_date}"

	letterhead_image = frappe.db.get_value("Letter Head", {"is_default": True}, "image")
	site_url = frappe.utils.get_url()
	if letterhead_image and not letterhead_image.startswith("http"):
		letterhead_image = site_url + letterhead_image

	data = data.get("data")["data"]

	department_data, department_grand_totals = get_department_summary(data)

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M:%S %p")
	company_name = frappe.defaults.get_global_default("company").replace("City of ", "")
	company_name = f"City of {company_name}"

	# Template path is hardcoded and bundled with the app, not user-controlled.
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	template = frappe.get_template(
		"us_payroll/us_payroll/report/payroll_detail_report_by_posted_date/payroll_detail_report_by_posted_date.html"
	)

	html = template.render(
		{
			"data": data,
			"department_data": department_data,
			"grand_totals": department_grand_totals,
			"filter": filters,
			"formatted_date_range": formatted_date_range,
			"current_datetime": formatted_datetime,
			"company_name": company_name,
			"from_date": from_date,
			"to_date": to_date,
			"letterhead_image": letterhead_image,
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
			"department_description": "",
			"employee_count": 0,
			"rate": 0.0,
			"net_pay": 0.0,
			"gross_pay": 0.0,
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
		summary["rate"] += float(row.get("rate") or 0)
		summary["net_pay"] += float(row.get("net_pay") or 0)
		summary["gross_pay"] += float(row.get("gross_pay") or 0)

		summary["employees"].append(
			{
				"employee_id": row.get("employee"),
				"employee_name": row.get("employee_name"),
				"rate": float(row.get("rate") or 0),
				"net_pay": float(row.get("net_pay") or 0),
				"gross_pay": float(row.get("gross_pay") or 0),
				"department_code_name": department_code_name,
			}
		)

	department_list = list(department_summary.values())
	department_list.sort(
		key=lambda x: (x["department_code"].zfill(5)) if x["department_code"].isdigit() else "99999"
	)

	grand_totals = {
		"employee_count": sum(d["employee_count"] for d in department_list),
		"rate_total": sum(d["rate"] for d in department_list),
		"total_net_pay": sum(d["net_pay"] for d in department_list),
		"total_gross_pay": sum(d["gross_pay"] for d in department_list),
	}

	return department_list, grand_totals
