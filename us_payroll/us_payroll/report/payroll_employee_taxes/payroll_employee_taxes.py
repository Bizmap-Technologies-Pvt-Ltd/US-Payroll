# Copyright (c) 2025, bizmap and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_data(filters):
	conditions = ["cs.docstatus = 1", "cs.posting_date BETWEEN %(from_date)s AND %(to_date)s"]

	if filters.get("department"):
		conditions.append("cs.department = %(department)s")

	condition_sql = " AND ".join(conditions)

	results = frappe.db.sql(
		f"""
		SELECT 
			agg.employee,
			agg.employee_name,
			agg.department AS department,
			SUM(agg.gross_pay) AS gross_pay,
			SUM(agg.federal_withholding) AS federal_withholding,
			SUM(agg.custom_total_pretax) AS pre_tax,
			SUM(agg.custom_total_non_taxable_earnings) AS non_taxable_earnings,
			SUM(agg.custom_taxable_wages) AS taxable_wages,

			SUM(
				CASE
					WHEN agg.custom_taxable_wages IS NOT NULL
					     AND agg.custom_taxable_wages > 0
					THEN agg.custom_taxable_wages
					ELSE (agg.gross_pay - IFNULL(agg.custom_total_non_taxable_earnings, 0))
				END
			) AS wages_tips_compensation,

			SUM(
				CASE
					WHEN agg.custom_ss_taxable_wages IS NOT NULL
					     AND agg.custom_ss_taxable_wages > 0
					THEN agg.custom_ss_taxable_wages
					ELSE IFNULL(agg.ss_employee_total, 0) / 0.062
				END
			) AS ss_wages,

			SUM(
				CASE
					WHEN agg.custom_mc_taxable_wages IS NOT NULL
					     AND agg.custom_mc_taxable_wages > 0
					THEN agg.custom_mc_taxable_wages
					ELSE IFNULL(agg.medicare_employee_total, 0) / 0.0145
				END
			) AS medicare_wages_tips,

			SUM(agg.ss_employee_total) AS social_security_emp,
			SUM(agg.ss_employer_total) AS social_security_er,
			SUM(agg.medicare_employee_total) AS medicare_emp,
			SUM(agg.medicare_employer_total) AS medicare_er
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
				cs.custom_ss_taxable_wages,
				cs.custom_mc_taxable_wages,

				COALESCE((
					SELECT SUM(ded.amount)
					FROM `tabSalary Detail` ded
					LEFT JOIN `tabSalary Component` sc ON ded.salary_component = sc.name
					WHERE ded.parent = cs.name
					AND sc.custom_federal_income_tax_and_additional_withholdings = 1
				), 0) AS federal_withholding,

				COALESCE((
					SELECT SUM(ded.amount)
					FROM `tabSalary Detail` ded
					LEFT JOIN `tabSalary Component` sc ON ded.salary_component = sc.name
					WHERE ded.parent = cs.name
					AND sc.name = 'Social Security Tax - Employee'
				), 0) AS ss_employee_total,

				COALESCE((
					SELECT SUM(ded.amount)
					FROM `tabSalary Detail` ded
					LEFT JOIN `tabSalary Component` sc ON ded.salary_component = sc.name
					WHERE ded.parent = cs.name
					AND sc.name = 'Social Security Tax - Employer'
				), 0) AS ss_employer_total,

				COALESCE((
					SELECT SUM(ded.amount)
					FROM `tabSalary Detail` ded
					LEFT JOIN `tabSalary Component` sc ON ded.salary_component = sc.name
					WHERE ded.parent = cs.name
					AND sc.name = 'Medicare Tax EE'
				), 0) AS medicare_employee_total,

				COALESCE((
					SELECT SUM(ded.amount)
					FROM `tabSalary Detail` ded
					LEFT JOIN `tabSalary Component` sc ON ded.salary_component = sc.name
					WHERE ded.parent = cs.name
					AND sc.name = 'Medicare Tax ER'
				), 0) AS medicare_employer_total

			FROM `tabSalary Slip` cs
			LEFT JOIN `tabEmployee` emp ON emp.name = cs.employee
			WHERE cs.docstatus = 1
			AND cs.posting_date BETWEEN %(from_date)s AND %(to_date)s
			{"AND emp.department = %(department_name)s" if filters.get("department_name") else ""}
		) agg
		GROUP BY agg.employee, agg.employee_name, agg.department
		ORDER BY agg.employee_name
	""",
		filters,
		as_dict=True,
	)

	social_security_wages_amt = 0
	medicare_wages_and_tips = 0
	wages_tips_compensation = 0
	ss_wages = 0
	medicare_wages_tips = 0

	for row in results:
		social_security_wages_amt = (row.get("social_security_emp") or 0) + (
			row.get("social_security_er") or 0
		)
		medicare_wages_and_tips = (row.get("medicare_emp") or 0) + (row.get("medicare_er") or 0)

		ss_taxable_amount = social_security_wages_amt / 0.124
		med_taxable_amount = medicare_wages_and_tips / 0.029

		if ss_taxable_amount:
			row["taxable_wages"] = ss_taxable_amount
		else:
			row["taxable_wages"] = med_taxable_amount

		# row["wages_tips_compensation"] = 0
		# row["ss_wages"] = (row.get("social_security_emp") or 0) / 0.062
		# row["medicare_wages_tips"] = (row.get("medicare_emp") or 0)/  0.0145

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
			"width": 100,
			"align": "right",
		},
		{
			"label": _("Pre-Tax"),
			"fieldname": "pre_tax",
			"fieldtype": "Currency",
			"width": 100,
			"align": "right",
		},
		{
			"label": _("Non-Taxable Earnings"),
			"fieldname": "non_taxable_earnings",
			"fieldtype": "Currency",
			"width": 140,
			"align": "right",
		},
		{
			"label": _("Taxable Wages"),
			"fieldname": "taxable_wages",
			"fieldtype": "Currency",
			"width": 140,
			"align": "right",
		},
		{
			"label": _("Federal Withholding"),
			"fieldname": "federal_withholding",
			"fieldtype": "Currency",
			"width": 170,
			"align": "right",
		},
		{
			"label": _("Social Security - Employee"),
			"fieldname": "social_security_emp",
			"fieldtype": "Currency",
			"width": 200,
			"align": "right",
		},
		{
			"label": _("Social Security - Employer"),
			"fieldname": "social_security_er",
			"fieldtype": "Currency",
			"width": 200,
			"align": "right",
		},
		{
			"label": _("Medicare - Employee"),
			"fieldname": "medicare_emp",
			"fieldtype": "Currency",
			"width": 170,
			"align": "right",
		},
		{
			"label": _("Medicare - Employer"),
			"fieldname": "medicare_er",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
		{
			"label": _("Wages, tips, other compensation"),
			"fieldname": "wages_tips_compensation",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
		{
			"label": _("Social security wages"),
			"fieldname": "ss_wages",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
		{
			"label": _("Medicare wages and tips"),
			"fieldname": "medicare_wages_tips",
			"fieldtype": "Currency",
			"width": 180,
			"align": "right",
		},
	]

	return columns
