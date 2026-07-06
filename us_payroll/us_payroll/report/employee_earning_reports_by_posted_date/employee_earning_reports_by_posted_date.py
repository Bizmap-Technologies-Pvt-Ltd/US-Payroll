# Copyright (c) 2026, bizmap and contributors
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
	# conditions = ["cs.docstatus = 1", "cs.posting_date BETWEEN %(from_date)s AND %(to_date)s"]

	results = frappe.db.sql(
		"""
		SELECT
			agg.employee,
			agg.employee_name,
			agg.department AS department,
			SUM(agg.gross_pay) AS gross_pay,
			SUM(agg.hourly) AS hourly,
			SUM(agg.overtime) AS overtime,
			SUM(agg.ct) AS ct,
			SUM(agg.pto) AS pto,
			SUM(agg.holiday_pay) AS holiday_pay,
			SUM(agg.cell_phone) AS cell_phone,
			SUM(agg.vehicle) AS vehicle,
			SUM(agg.administrative_stipend) AS administrative_stipend,
			SUM(agg.certificate_pay) AS certificate_pay,
			SUM(agg.tmrs_fix) AS tmrs_fix,
			SUM(agg.holiday_pay_m) AS holiday_pay_m,
			SUM(agg.payroll_correction) AS payroll_correction,
			SUM(agg.sick_leave) AS sick_leave,
			SUM(agg.pr_adj) AS pr_adj,
			SUM(agg.fed_withholding_fix) AS fed_withholding_fix,
			SUM(agg.vehicle_allowance) AS vehicle_allowance,
			SUM(agg.elected) AS elected,
			SUM(agg.salary) AS salary,
			SUM(agg.leave_encashment) AS leave_encashment,
			SUM(agg.arrear) AS arrear,
			SUM(agg.basic) AS basic

		FROM (
			SELECT
				cs.name AS salary_slip_id,
				cs.employee,
				cs.employee_name,
				emp.department,
				cs.gross_pay,
				cs.custom_total_pretax,
				cs.custom_total_non_taxable_earnings,
				cs.custom_taxable_wages,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Hourly'
				), 0) AS hourly,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Overtime'
				), 0) AS overtime,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'CT'
				), 0) AS ct,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'PTO'
				), 0) AS pto,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Holiday Pay'
				), 0) AS holiday_pay,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Cell Phone'
				), 0) AS cell_phone,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Vehicle'
				), 0) AS vehicle,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Administrative Stipend'
				), 0) AS administrative_stipend,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Certificate Pay'
				), 0) AS certificate_pay,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'TMRS FIX'
				), 0) AS tmrs_fix,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Holiday Pay M'
				), 0) AS holiday_pay_m,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Payroll Correction'
				), 0) AS payroll_correction,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Sick Leave'
				), 0) AS sick_leave,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'PR ADJ'
				), 0) AS pr_adj,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Fed Withholding Fix'
				), 0) AS fed_withholding_fix,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Vehicle Allowance'
				), 0) AS vehicle_allowance,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Elected'
				), 0) AS elected,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Salary'
				), 0) AS salary,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Leave Encashment'
				), 0) AS leave_encashment,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Arrear'
				), 0) AS arrear,

				COALESCE((
					SELECT SUM(earn.amount)
					FROM `tabSalary Detail` earn
					LEFT JOIN `tabSalary Component` sc ON earn.salary_component = sc.name
					WHERE earn.parent = cs.name
					AND sc.name = 'Basic'
				), 0) AS basic

			FROM `tabSalary Slip` cs
			LEFT JOIN `tabEmployee` emp ON emp.name = cs.employee
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
			"label": _("Hourly"),
			"fieldname": "hourly",
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
		},
		{
			"label": _("Overtime"),
			"fieldname": "overtime",
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
		},
		# {"label": _("CT"), "fieldname": "ct", "fieldtype": "Currency", "width": 140, "align": "right"},
		{"label": _("PTO"), "fieldname": "pto", "fieldtype": "Currency", "width": 140, "align": "right"},
		{
			"label": _("Salary"),
			"fieldname": "salary",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
		{
			"label": _("Leave Encashment"),
			"fieldname": "leave_encashment",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
		{
			"label": _("Arrear"),
			"fieldname": "arrear",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
		{"label": _("Basic"), "fieldname": "basic", "fieldtype": "Currency", "width": 180, "align": "right"},
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

	formatted_start_date = from_date.strftime("%m/%d/%Y")
	formatted_end_date = to_date.strftime("%m/%d/%Y")
	formatted_start_end_date = f"{formatted_start_date} - {formatted_end_date}"

	template_path = "us_payroll/us_payroll/report/employee_earning_reports_by_posted_date/employee_earning_reports_by_posted_date.html"

	data = data.get("data")["data"]

	current_datetime = datetime.now()
	formatted_datetime = current_datetime.strftime("%-m/%-d/%Y %-I:%M%p").lower()

	company_name = frappe.defaults.get_global_default("company").replace("City of ", "")
	company_name = f"City of {company_name}"

	# Template path is hardcoded and bundled with the app, not user-controlled.
	html = frappe.render_template(  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		template_path,
		{
			"data": data,
			"company_name": company_name,
			"formatted_start_end_date": formatted_start_end_date,
			"formatted_datetime": formatted_datetime,
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
	return {"data": data, "html": html, "pdf_file": pdf_file}
