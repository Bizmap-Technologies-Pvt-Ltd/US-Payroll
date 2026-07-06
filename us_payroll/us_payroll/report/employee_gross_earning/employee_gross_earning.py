# Copyright (c) 2025, bizmap and contributors
# For license information, please see license.txt

import calendar
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.utils.pdf import get_pdf


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	results = frappe.db.sql(
		"""
		SELECT
			agg.employee,
			agg.employee_name,
			agg.department AS department,
			SUM(agg.gross_pay) AS gross_pay

		FROM (
			SELECT
				cs.name AS salary_slip_id,
				cs.employee,
				cs.employee_name,
				emp.department,
				cs.gross_pay

			FROM `tabSalary Slip` cs
			LEFT JOIN `tabEmployee` emp ON emp.name = cs.employee
			WHERE cs.docstatus = 1
			AND cs.start_date BETWEEN %(from_date)s AND %(to_date)s

		) agg
		GROUP BY agg.employee, agg.employee_name
		ORDER BY agg.employee_name
	""",
		filters,
		as_dict=True,
	)

	return results


def get_columns():
	columns = [
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200,
			"align": "left",
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"width": 150,
			"align": "left",
		},
		{
			"label": _("Gross Pay"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 150,
			"align": "right",
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
	filters = data.get("filter", {})

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if isinstance(from_date, str):
		from_date = datetime.strptime(from_date, "%Y-%m-%d")
	if isinstance(to_date, str):
		to_date = datetime.strptime(to_date, "%Y-%m-%d")

	# Format without time, in MM/DD/YYYY
	formatted_start_date = from_date.strftime("%m/%d/%Y")
	formatted_end_date = to_date.strftime("%m/%d/%Y")
	formatted_start_end_date = f"{formatted_start_date} - {formatted_end_date}"

	letterhead_image = frappe.db.get_value("Letter Head", {"is_default": True}, "image")
	site_url = frappe.utils.get_url()
	if letterhead_image and not letterhead_image.startswith("http"):
		letterhead_image = site_url + letterhead_image

	template_path = "us_payroll/us_payroll/report/employee_gross_earning/employee_gross_earning.html"

	data = data.get("data")["data"]

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M%p").lower()

	company_name = frappe.defaults.get_global_default("company").replace("City of ", "")
	company_name = f"City of {company_name}"

	# Template path is hardcoded and bundled with the app, not user-controlled.
	html = frappe.render_template(  # nosemgrep: frappe-ssti
		template_path,
		{
			"data": data,
			"company_name": company_name,
			"formatted_start_end_date": formatted_start_end_date,
			"formatted_datetime": formatted_datetime,
			"letterhead_image": letterhead_image,
		},
	)

	options = {
		"page-width": "1500px",
		"page-height": "1500px",
		"orientation": "Landscape",
		"margin-right": "20mm",
		"margin-left": "20mm",
	}

	pdf_file = get_pdf(html, options=options)
	return {"data": data, "html": html, "pdf_file": pdf_file}
