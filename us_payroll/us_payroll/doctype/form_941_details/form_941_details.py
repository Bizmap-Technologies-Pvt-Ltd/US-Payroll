# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from datetime import datetime

class Form941Details(Document):
	pass

@frappe.whitelist()
def calculate_totals(doc):	
	doc = json.loads(doc)
	if doc.get("year"):
		doc["year"] = int(doc["year"])
	if not (doc.get("year_start_date") and doc.get("year_end_date")):
		frappe.throw("Please make sure Year Start Date, and Year End Date are set.")
 
	start_date = doc.get("year_start_date")
	end_date = doc.get("year_end_date")

	if doc.get("january_february_march"):
		start_date = datetime(doc.get("year"), 1, 1)
		end_date = datetime(doc.get("year"), 3, 31)
	elif doc.get("april_may_june"):
		start_date = datetime(doc.get("year"), 4, 1)
		end_date = datetime(doc.get("year"), 6, 30)
	elif doc.get("july_august_september"):
		start_date = datetime(doc.get("year"), 7, 1)
		end_date = datetime(doc.get("year"), 9, 30)
	elif doc.get("october_november_december"):
		start_date = datetime(doc.get("year"), 10, 1)
		end_date = datetime(doc.get("year"), 12, 31)
 
	conditions = [
		"cs.docstatus = 1",
		"cs.posting_date BETWEEN %(start_date)s AND %(end_date)s"
	]
 
	condition_sql = " AND ".join(conditions)
 
	results = frappe.db.sql(f"""
		SELECT 
			agg.employee,
			agg.employee_name,
			agg.department,
			SUM(agg.gross_pay) AS gross_pay,
			SUM(agg.federal_withholding) AS federal_withholding,
			SUM(agg.custom_total_pretax) AS pre_tax,
			SUM(agg.custom_total_non_taxable_earnings) AS non_taxable_earnings,
			SUM(agg.custom_taxable_wages) AS taxable_wages,
			SUM(agg.ss_employee_total) AS social_security_emp,
			SUM(agg.ss_employer_total) AS social_security_er,
			SUM(agg.medicare_employee_total) AS medicare_emp,
			SUM(agg.medicare_employer_total) AS medicare_er
		FROM (
			SELECT 
				cs.name AS salary_slip_id,
				cs.employee,
				cs.employee_name,
				cs.department,
				cs.gross_pay,
				cs.custom_total_pretax,
				cs.custom_total_non_taxable_earnings,
				cs.custom_taxable_wages,
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
			WHERE {condition_sql}
		) agg
		GROUP BY agg.employee, agg.employee_name, agg.department
		ORDER BY agg.employee_name
	""", {
			"start_date": start_date,
			"end_date": end_date
		}, as_dict=True)
 
	total_gross_pay = 0.0
	total_pretax = 0.0
	total_taxable_wages = 0.0
	total_non_taxable_earnings = 0.0
	total_federal_income_tax_withheld = 0.0
	social_security_wages_amt = 0.0
	medicare_wages_and_tips = 0.0

	for row in results:
		total_gross_pay += (row.get("gross_pay") or 0)
		total_pretax += (row.get("custom_total_pretax") or 0)
		total_taxable_wages += (row.get("taxable_wages") or 0)
		total_non_taxable_earnings += (row.get("non_taxable_earnings") or 0)
		total_federal_income_tax_withheld += (row.get("federal_withholding") or 0)
		social_security_wages_amt += (row.get("social_security_emp") or 0) + (row.get("social_security_er") or 0)
		medicare_wages_and_tips += (row.get("medicare_emp") or 0) + (row.get("medicare_er") or 0)
 
	ss_taxable_amount = social_security_wages_amt / 0.124
	med_taxable_amount = medicare_wages_and_tips / 0.029
	
	taxable_wages = 0.0
	taxable_wages_medicare = 0.0
	if ss_taxable_amount:
		taxable_wages = ss_taxable_amount
	if med_taxable_amount:
		taxable_wages_medicare = med_taxable_amount
	return {
			"total_gross_pay": total_gross_pay, 
			"total_federal_income_tax_withheld" : total_federal_income_tax_withheld,
			"social_security_wages_amt":social_security_wages_amt, 
			"medicare_wages_and_tips": medicare_wages_and_tips, 
			"taxable_wages": taxable_wages, 
			"taxable_wages_medicare":taxable_wages_medicare
		}


@frappe.whitelist()
def fetch_address_details(is_your_company_address, link_doctype, link_name):	
	address = frappe.db.sql(f""" 
			SELECT a.address_line1, a.address_line2, a.city, a.state, a.county, a.country, a.pincode, a.email_id,a.phone
			FROM `tabAddress` a
			JOIN `tabDynamic Link` l ON l.parent = a.name
			WHERE a.is_your_company_address = 1
			  AND l.link_doctype = 'Company'
			  AND l.link_name = %(employer_name)s
		""", {"employer_name": link_name},as_dict=1)

	for add in address:
		if add:
			address_line1 = add.get("address_line1") or ""
			address_line2 = add.get("address_line2") or ""
			city = add.get("city") or ""
			state = add.get("state") or ""
			country = add.get("country") or ""
			county = add.get("county") or ""
			pincode = add.get("pincode") or ""

			email_id = add.get("email_id") or ""
			phone = add.get("phone") or ""

			complete_address = ", ".join(filter(None, [address_line1, address_line2, city, state, country, pincode]))

			return {
					"complete_address" : complete_address,
					"address_line1" : address_line1,
					"address_line2" : address_line2,
					"city" : city,
					"state" : state,
					"county" : county,
					"country" : country,
					"pincode" : pincode,
					"email_id" : email_id,
					"phone" : phone
					}

	return {
			"complete_address" : "",
			"address_line1" : "",
			"address_line2" : "",
			"city" : "",
			"state" : "",
			"county" : "",
			"country" : "",
			"pincode" : "",
			"email_id" : "",
			"phone" : "",
			}

@frappe.whitelist()
def get_quarterly_data_for_liability(doc):
	doc = json.loads(doc)
	if doc.get("year"):
		doc["year"] = int(doc["year"])

	if not (doc.get("year_start_date") and doc.get("year_end_date")):
		frappe.throw("Please make sure Year Start Date, and Year End Date are set.")

	start_date = doc.get("year_start_date")
	end_date = doc.get("year_end_date")

	if doc.get("january_february_march"):
		start_date = datetime(doc.get("year"), 1, 1)
		end_date = datetime(doc.get("year"), 3, 31)
		month_mapping = {1: "first_month", 2: "second_month", 3: "third_month"}

	elif doc.get("april_may_june"):
		start_date = datetime(doc.get("year"), 4, 1)
		end_date = datetime(doc.get("year"), 6, 30)
		month_mapping = {4: "first_month", 5: "second_month", 6: "third_month"}

	elif doc.get("july_august_september"):
		start_date = datetime(doc.get("year"), 7, 1)
		end_date = datetime(doc.get("year"), 9, 30)
		month_mapping = {7: "first_month", 8: "second_month", 9: "third_month"}

	elif doc.get("october_november_december"):
		start_date = datetime(doc.get("year"), 10, 1)
		end_date = datetime(doc.get("year"), 12, 31)
		month_mapping = {10: "first_month", 11: "second_month", 12: "third_month"}

	salary_slips = frappe.get_all("Salary Slip",
								  filters={
									  "posting_date": ["between", [start_date, end_date]],
									  "docstatus": 1
								  },
								  fields=["name", "employee", "start_date", "gross_pay"]
								  )

	employee_ids = {slip['employee'] for slip in salary_slips}
	unique_employee_count = len(employee_ids)
	print("Unique Employee Count in a quarter:", unique_employee_count)

	total_amt = 0
	monthly_totals = {"first_month": 0, "second_month": 0, "third_month": 0}

	for slip in salary_slips:
		slip_doc = frappe.get_doc("Salary Slip", slip['name'])
		slip_month = slip_doc.start_date.month
		month_key = month_mapping.get(slip_month)

		for row in slip_doc.deductions:
			if row.salary_component in ["Social Security Tax - Employee", "Social Security Tax - Employer", "Medicare Tax EE", "Medicare Tax ER", "FIT Withholdings", "FIT"]:
				total_amt += row.amount
				if month_key:
					monthly_totals[month_key] += row.amount

	# =============================employee count=============================
	year = int(doc.get("year"))

	quarter_date_map = {
		"january_february_march": datetime(year, 3, 12),
		"april_may_june": datetime(year, 6, 12),
		"july_august_september": datetime(year, 9, 12),
		"october_november_december": datetime(year, 12, 12),
	}

	target_date = None
	for key, date in quarter_date_map.items():
		if doc.get(key):
			target_date = date
			break

	if not target_date:
		frappe.throw("Quarter not selected properly.")

	# Get salary slips overlapping the target date
	salary_slips = frappe.get_all("Salary Slip",
								  filters={
									  "posting_date": ["between", [start_date, target_date]],
									  # "start_date": ["<=", target_date],
									  # "end_date": [">=", target_date],
									  "docstatus": 1
								  },
								  fields=["employee"]
								  )
	active_employees = set()
	for slip in salary_slips:
		employee = slip["employee"]
		relieving_date = frappe.db.get_value("Employee", employee, "relieving_date")

		# Include if not relieved before the 12th
		if not relieving_date or relieving_date >= target_date.date():
			active_employees.add(employee)

	employee_list = sorted(list(active_employees))

	return {
		"total_amt": total_amt,
		"first_month": monthly_totals["first_month"],
		"second_month": monthly_totals["second_month"],
		"third_month": monthly_totals["third_month"],
		"employee_count": len(employee_list),
		"employees": employee_list,
		"target_date": target_date.strftime("%Y-%m-%d")
	}

# @frappe.whitelist()
# def get_active_employees_on_12th(doc):
# 	doc = json.loads(doc)
# 	year = int(doc.get("year"))
#
# 	quarter_date_map = {
# 		"january_february_march": datetime(year, 3, 12),
# 		"april_may_june": datetime(year, 6, 12),
# 		"july_august_september": datetime(year, 9, 12),
# 		"october_november_december": datetime(year, 12, 12),
# 	}
#
# 	# Determine the correct target date
# 	target_date = None
# 	for key, date in quarter_date_map.items():
# 		if doc.get(key):
# 			target_date = date
# 			break
#
# 	if not target_date:
# 		frappe.throw("Quarter not selected properly.")
#
# 	# Get salary slips overlapping the target date
# 	salary_slips = frappe.get_all("Salary Slip",
# 		filters={
# 			"start_date": ["<=", target_date],
# 			"end_date": [">=", target_date],
# 			"docstatus": 1
# 		},
# 		fields=["employee"]
# 	)
#
# 	active_employees = set()
#
# 	for slip in salary_slips:
# 		employee = slip["employee"]
# 		relieving_date = frappe.db.get_value("Employee", employee, "relieving_date")
#
# 		# Include if not relieved before the 12th
# 		if not relieving_date or relieving_date >= target_date.date():
# 			active_employees.add(employee)
#
# 	# Convert set to sorted list for consistency
# 	employee_list = sorted(list(active_employees))
# 	print(employee_list, len(employee_list), "******************************len(employee_list)")
#
# 	return {
# 		"employee_count": len(employee_list),
# 		"employees": employee_list,
# 		"target_date": target_date.strftime("%Y-%m-%d")
# 	}
