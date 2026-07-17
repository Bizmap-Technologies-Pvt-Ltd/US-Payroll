# Copyright (c) 2026, Bizmap Technologies and contributors
# For license information, please see license.txt

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate

# WORKERS_COMP_REPORT_TEMPLATE = "us_payroll/us_payroll/report/workers_comp_report/workers_comp_report.html"
from frappe.utils.jinja import get_jenv
from frappe.utils.pdf import get_pdf


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Comp Code"),
			"fieldname": "custom_comp_code",
			"fieldtype": "Link",
			"options": "Comp Code",
			"width": 120,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"label": _("Earnings"),
			"fieldname": "earnings",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Hours"),
			"fieldname": "hours",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("OT Rate"),
			"fieldname": "ot_rate",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("OT Hours"),
			"fieldname": "ot_hours",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("OT Amount"),
			"fieldname": "ot_amount",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Gross Amount"),
			"fieldname": "gross_amount",
			"fieldtype": "Currency",
			"width": 150,
		},
	]


def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not from_date or not to_date:
		frappe.throw(_("Please set From Date and To Date filters"))

	results = frappe.db.sql(
		"""
		SELECT
			agg.employee,
			agg.employee_name,
			agg.department AS department,
			agg.custom_comp_code AS custom_comp_code,
			ROUND(SUM(agg.gross_pay), 2) AS gross_amount,
			ROUND(SUM(agg.custom_custom_total_working_hours), 2) AS hours,
			agg.custom_custom_overtime_hourly_rate AS ot_rate,
			ROUND(SUM(agg.custom_custom_total_overtime_hours), 2) AS ot_hours,
			ROUND(SUM(agg.custom_total_overtime_amount), 2) AS ot_amount,
			ROUND(SUM(agg.gross_pay) - SUM(agg.custom_total_overtime_amount), 2) AS earnings
		FROM (
			SELECT
				cs.name AS salary_slip_id,
				cs.employee,
				cs.employee_name,
				emp.department,
				emp.custom_comp_code,
				cs.gross_pay,
				cs.custom_custom_total_working_hours,
				cs.custom_custom_overtime_hourly_rate,
				cs.custom_custom_total_overtime_hours,
				cs.custom_total_overtime_amount,
				ct.cost_center_name
			FROM `tabSalary Slip` cs
			LEFT JOIN `tabEmployee` emp ON emp.name = cs.employee
			LEFT JOIN `tabCost Center` ct ON ct.name = emp.department
			WHERE cs.docstatus = 1
			AND cs.posting_date BETWEEN %(from_date)s AND %(to_date)s
		) agg
		GROUP BY agg.employee, agg.employee_name
		ORDER BY agg.employee_name
	""",
		filters,
		as_dict=True,
	)

	return results


@frappe.whitelist()
def get_print(report_data: str):
	report_data = json.loads(report_data)
	filters = report_data.get("filter")
	report_data = {"filter": filters, "data": report_data.get("data")}
	return generate_pdf(report_data)


@frappe.whitelist()
def generate_pdf(data: dict[str, Any]):
	filters = data.get("filter")

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	from_date = datetime.strptime(from_date, "%Y-%m-%d")
	to_date = datetime.strptime(to_date, "%Y-%m-%d")
	formatted_from_date = from_date.strftime("%m/%d/%Y")
	formatted_to_date = to_date.strftime("%m/%d/%Y")
	formatted_date_range = f"{formatted_from_date} - {formatted_to_date}"

	letterhead_image = frappe.db.get_value("Letter Head", {"is_default": True}, "image")
	site_url = frappe.utils.get_url()
	if letterhead_image and not letterhead_image.startswith("http"):
		letterhead_image = site_url + letterhead_image

	data = data.get("data")

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M:%S %p")
	company_name = frappe.defaults.get_global_default("company").replace("City of ", "")
	company_name = f"City of {company_name}"
	department_data, comp_code_summary, department_summary, grand_totals = get_department_summary(data)

	# Template path is hardcoded and bundled with the app, not user-controlled.
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	# html = frappe.render_template(
	# 	WORKERS_COMP_REPORT_TEMPLATE,
	# 	{
	# 		"data": data,
	# 		"department_data": department_data,
	# 		"comp_code_summary": comp_code_summary,
	# 		"department_summary": department_summary,
	# 		"grand_totals": grand_totals,
	# 		"filter": filters,
	# 		"formatted_date_range": formatted_date_range,
	# 		"current_datetime": formatted_datetime,
	# 		"company_name": company_name,
	# 		"letterhead_image": letterhead_image,
	# 	},
	# )

	template = frappe.get_template(
		"us_payroll/us_payroll/report/workers_comp_report/workers_comp_report.html"
	)

	html = template.render(
		{
			"data": data,
			"department_data": department_data,
			"comp_code_summary": comp_code_summary,
			"department_summary": department_summary,
			"grand_totals": grand_totals,
			"filter": filters,
			"formatted_date_range": formatted_date_range,
			"current_datetime": formatted_datetime,
			"company_name": company_name,
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
		"comp_code_summary": comp_code_summary,
		"department_summary": department_summary,
		"grand_totals": grand_totals,
		"html": html,
		"pdf_file": pdf_file,
	}


def get_department_summary(data):
	department_summary = defaultdict(
		lambda: {
			"department_code": "",
			"comp_codes": defaultdict(
				lambda: {
					"comp_code": "",
					"employees": [],
					"employee_count": 0,
					"earnings": 0.0,
					"hours": 0.0,
					"ot_amount": 0.0,
					"ot_hours": 0.0,
					"gross_amount": 0.0,
				}
			),
		}
	)

	# --- Build department + comp code structure ---
	for row in data:
		dept_code = row.get("department") or "Unknown"
		comp_code = row.get("custom_comp_code") or "NA"

		if "Unknown" in (dept_code):
			continue

		summary = department_summary[dept_code]
		summary["department_code"] = dept_code

		comp_summary = summary["comp_codes"][comp_code]
		comp_summary["comp_code"] = comp_code

		comp_summary["employees"].append(
			{
				"employee_id": row.get("employee"),
				"employee_name": row.get("employee_name"),
				"earnings": float(row.get("earnings") or 0),
				"hours": float(row.get("hours") or 0),
				"ot_amount": float(row.get("ot_amount") or 0),
				"ot_hours": float(row.get("ot_hours") or 0),
				"gross_amount": float(row.get("gross_amount") or 0),
			}
		)

		comp_summary["employee_count"] += 1
		comp_summary["earnings"] += float(row.get("earnings") or 0)
		comp_summary["hours"] += float(row.get("hours") or 0)
		comp_summary["ot_amount"] += float(row.get("ot_amount") or 0)
		comp_summary["ot_hours"] += float(row.get("ot_hours") or 0)
		comp_summary["gross_amount"] += float(row.get("gross_amount") or 0)

	department_list = list(department_summary.values())

	# --- Build Comp Code Summary (merged across all departments) ---
	comp_code_summary = defaultdict(
		lambda: {
			"comp_code": "",
			"employee_count": 0,
			"earnings": 0.0,
			"hours": 0.0,
			"ot_amount": 0.0,
			"ot_hours": 0.0,
			"gross_amount": 0.0,
		}
	)

	for dept in department_list:
		for comp in dept["comp_codes"].values():
			summary = comp_code_summary[comp["comp_code"]]
			summary["comp_code"] = comp["comp_code"]
			summary["employee_count"] += comp["employee_count"]
			summary["earnings"] += comp["earnings"]
			summary["hours"] += comp["hours"]
			summary["ot_amount"] += comp["ot_amount"]
			summary["ot_hours"] += comp["ot_hours"]
			summary["gross_amount"] += comp["gross_amount"]

	comp_code_summary_list = list(comp_code_summary.values())

	# --- Build Department Summary (merged across comp codes) ---
	department_summary_list = []
	for dept in department_list:
		totals = {
			"department_code": dept["department_code"],
			"employee_count": sum(comp["employee_count"] for comp in dept["comp_codes"].values()),
			"earnings": sum(comp["earnings"] for comp in dept["comp_codes"].values()),
			"hours": sum(comp["hours"] for comp in dept["comp_codes"].values()),
			"ot_amount": sum(comp["ot_amount"] for comp in dept["comp_codes"].values()),
			"ot_hours": sum(comp["ot_hours"] for comp in dept["comp_codes"].values()),
			"gross_amount": sum(comp["gross_amount"] for comp in dept["comp_codes"].values()),
		}
		department_summary_list.append(totals)

	# --- Grand Totals ---
	grand_totals = {
		"employee_count": sum(d["employee_count"] for d in department_summary_list),
		"earnings": sum(d["earnings"] for d in department_summary_list),
		"hours": sum(d["hours"] for d in department_summary_list),
		"ot_amount": sum(d["ot_amount"] for d in department_summary_list),
		"ot_hours": sum(d["ot_hours"] for d in department_summary_list),
		"gross_amount": sum(d["gross_amount"] for d in department_summary_list),
	}

	return department_list, comp_code_summary_list, department_summary_list, grand_totals
