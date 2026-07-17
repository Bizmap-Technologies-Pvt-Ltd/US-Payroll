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
	if not filters:
		return [], []

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Employee name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Gross Wages"),
			"fieldname": "gross_pay",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("FIT withholdings"),
			"fieldname": "fit_withholdings",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Social Security Wages"),
			"fieldname": "social_security_wages",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Medicare Wages"),
			"fieldname": "medicare_wages",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Unemployment insurance"),
			"fieldname": "workers_comp",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Workers comp"),
			"fieldname": "unemployment_insurance",
			"fieldtype": "Currency",
			"width": 150,
		},
	]
	return columns


def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if not from_date or not to_date:
		frappe.throw(_("Please select both From Date and To Date."))

	data = frappe.db.sql(
		"""
		SELECT
			pe.name AS payroll_entry,
			ped.employee,
			ped.employee_name,
			emp.first_name,
			emp.middle_name,
			emp.last_name,
			gp.gross_pay,

			COALESCE(SUM(
				CASE
					WHEN sd.salary_component IN ('FIT Withholdings', 'FIT') THEN sd.amount
					ELSE 0
				END
			), 0) AS fit_withholdings,

			COALESCE(SUM(CASE
				WHEN sd.salary_component = 'Social Security Tax - Employee' THEN sd.amount
				ELSE 0 END), 0) AS social_security_wages,
			COALESCE(SUM(CASE
				WHEN sd.salary_component = 'Medicare Tax EE' THEN sd.amount
				ELSE 0 END), 0) AS medicare_wages

		FROM
			`tabPayroll Entry` pe
		JOIN
			`tabPayroll Employee Detail` ped ON ped.parent = pe.name
		LEFT JOIN
			`tabEmployee` emp ON emp.name = ped.employee

		LEFT JOIN (
			SELECT employee, SUM(gross_pay) AS gross_pay
			FROM `tabSalary Slip`
			WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
			  AND docstatus != 2
			GROUP BY employee
		) gp ON gp.employee = ped.employee

		LEFT JOIN
			`tabSalary Slip` cst ON cst.employee = ped.employee AND cst.payroll_entry = pe.name
		LEFT JOIN
			`tabSalary Detail` sd ON sd.parent = cst.name

		WHERE
			cst.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND cst.docstatus != 2
			AND sd.salary_component IN ('FIT Withholdings', 'Social Security Tax - Employee', 'Medicare Tax EE', 'FIT')

		GROUP BY
			ped.employee, gp.gross_pay

	""",
		{"from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	for row in data:
		row["workers_comp"] = (row.get("gross_pay") or 0) * 0.007
		row["unemployment_insurance"] = 0

	return data


@frappe.whitelist()
def get_print(report_data: str):
	report_data = json.loads(report_data)
	report_data = {"filter": report_data["filter"], "data": report_data}
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

	data = data.get("data")["data"]

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M%p").lower()

	# Template path is hardcoded and bundled with the app, not user-controlled.
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	template = frappe.get_template(
		"us_payroll/us_payroll/report/payroll_tax_summary_report/payroll_tax_summary_report.html"
	)

	html = template.render(
		{
			"data": data,
			"current_datetime": formatted_datetime,
			"formatted_date_range": formatted_date_range,
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

	return {"data": data, "html": html, "pdf_file": pdf_file}
