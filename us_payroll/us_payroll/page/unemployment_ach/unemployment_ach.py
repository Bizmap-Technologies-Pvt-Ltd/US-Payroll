import datetime
import io
import math
from calendar import monthrange
from datetime import datetime

import frappe
from frappe.utils.file_manager import save_file

from us_payroll.us_payroll.report.unemployment_report import unemployment_report


@frappe.whitelist()
def get_unemployment_report_data(year, quarter):
	filters = {"year": year, "quarter": quarter}
	columns, data = unemployment_report.execute(filters)

	if not data:
		frappe.throw("No data found for the selected period.")

	lines = []

	lines.append(generate_a_record(data))
	lines.append(generate_b_record(data))
	lines.append(generate_e_record(data))

	for emp in data:
		lines.append(generate_s_record(emp))

	lines.append(generate_t_record(data))
	lines.append(generate_f_record(data))

	content = "\n".join(lines)
	file_name = f"unemployment_report_{year}_Q{quarter}.txt"
	file_content = content.encode("utf-8")

	file_doc = save_file(
		fname=file_name, content=file_content, dt=None, dn=None, folder="Home/Attachments", is_private=1
	)

	return {"file_url": file_doc.file_url}


def pad(value, length, align="left", fillchar=" "):
	if align == "left":
		return str(value)[:length].ljust(length, fillchar)
	else:
		return str(value)[:length].rjust(length, fillchar)


# --- Record Generators ---
def generate_a_record(data):
	year = data[0]["print_data"][0]["year"]

	ach_details = frappe.get_single("ACH Report Details")

	company_id = ach_details.company_id or ""

	company_city_name = ach_details.company_city_name or ""

	address = ach_details.address or ""

	city = ach_details.city or ""

	city_code = ach_details.city_code or ""

	zipcode = ach_details.zipcode or ""

	contact = ach_details.contact or ""

	telephone_number = ach_details.telephone_number or ""

	taxing_entity_code = ach_details.taxing_entity_code or ""

	telephone_extension_box = ach_details.telephone_extension_box or ""

	C_3_data_indicator = "Y" or ""

	media_creation_date = datetime.datetime.today().strftime("%m%d%Y") or ""

	return (
		"A"
		+ pad(year, 4)
		+ pad(company_id, 9)
		+ pad(taxing_entity_code, 4)
		+ pad(" ", 5)
		+ pad(company_city_name, 50)
		+ pad(address, 40)
		+ pad(city, 25)
		+ pad(city_code, 2)
		+ pad(" ", 13)
		+ pad(zipcode, 5)
		+ pad(" ", 5)
		+ pad(contact, 30)
		+ pad(telephone_number, 10)
		+ pad(telephone_extension_box, 4)
		+ pad("", 6)
		+ pad(C_3_data_indicator, 1)
		+ pad(" ", 5)
		+ pad(" ", 1)
		+ pad(" ", 9)
		+ pad(" ", 28)
		+ pad(media_creation_date, 8)
	)


def generate_b_record(data):
	year = data[0]["print_data"][0]["year"]

	ach_details = frappe.get_single("ACH Report Details")

	company_id = ach_details.company_id or ""

	company_city_name = ach_details.company_city_name or ""

	computer = ach_details.computer or ""

	internal_label = ach_details.internal_label or ""

	density = ach_details.density or ""

	recording_code = ach_details.recording_code or ""

	number_of_tracks = ach_details.number_of_tracks or ""

	blocking_factor = ach_details.blocking_factor or ""

	taxing_entity_code = ach_details.taxing_entity_code or ""

	address = ach_details.address or ""

	city = ach_details.city or ""

	city_code = ach_details.city_code or ""

	zipcode = ach_details.zipcode or ""

	telephone_extension_box = ach_details.telephone_extension_box or ""

	return (
		"B"
		+ pad(year, 4)
		+ pad(company_id, 9)
		+ pad(computer, 8)
		+ pad(internal_label, 2)
		+ pad(" ", 1)
		+ pad(density, 2)
		+ pad(recording_code, 3)
		+ pad(number_of_tracks, 2)
		+ pad(blocking_factor, 2)
		+ pad(taxing_entity_code, 4)
		+ pad(" ", 108)
		+ pad(company_city_name, 44)
		+ pad(address, 35)
		+ pad(city, 20)
		+ pad(city_code, 2)
		+ pad(" ", 5)
		+ pad(zipcode, 5)
	)
	# pad(telephone_extension_box, 5) + \
	# pad(" ", 13)


def generate_e_record(data):
	year = data[0]["print_data"][0]["year"]

	ach_details = frappe.get_single("ACH Report Details")

	company_id = ach_details.company_id or ""

	# employer_name = ach_details.company_name or ""

	company_city_name = ach_details.company_city_name or ""

	type_of_employment = ach_details.type_of_employment or ""

	establishment_number_or_coverage_grouppru = ach_details.establishment_number_or_coverage_grouppru or ""

	blocking_factor = ach_details.blocking_factor or ""

	taxing_entity_code = ach_details.taxing_entity_code or ""

	address = ach_details.address or ""

	city = ach_details.city or ""

	city_code = ach_details.city_code or ""

	zipcode = ach_details.zipcode or ""

	telephone_extension_box = ach_details.telephone_extension_box or ""

	state_unemployment_insurance_account_number = (
		ach_details.state_unemployment_insurance_account_number or ""
	)

	naics_code = ach_details.naics_code or ""

	# reporting_period  = ach_details.reporting_period
	quarter = str(data[0].get("quarter", "")).strip()

	# Map quarter to last month of the quarter
	quarter_to_month = {"1": "03", "2": "06", "3": "09", "4": "12"}

	month = quarter_to_month.get(quarter, "")
	reporting_period = month

	no_workersno_wages = ach_details.no_workersno_wages or ""
	tax_type_code = ach_details.tax_type_code or ""
	taxing_entity_code = ach_details.taxing_entity_code or ""
	state_control_number = ach_details.state_control_number or ""
	unit_number = ach_details.unit_number or ""
	foreign_indicator = ach_details.foreign_indicator or ""
	other_ein = ach_details.other_ein or ""

	return (
		"E"
		+ pad(year, 4)
		+ pad(company_id, 9)
		+ pad(" ", 9)
		+ pad(company_city_name, 50)
		+ pad(address, 40)
		+ pad(city, 25)
		+ pad(city_code, 2)
		+ pad(" ", 8)
		+ pad(zipcode, 5)
		+ pad(" ", 1)
		+ pad(taxing_entity_code, 4)
		+ pad("48", 2)
		+ pad(state_unemployment_insurance_account_number, 9)
		+ pad(naics_code, 6)
		+ pad(reporting_period, 2)
		+ pad(no_workersno_wages, 1)
	)


def generate_s_record(emp):
	ssn = emp.get("custom_nomasked_social_security_number", "").replace("-", "").rjust(9, "0") or ""

	last_name = emp.get("last_name", "").ljust(20) or ""

	first_name = emp.get("first_name", "").ljust(15) or ""

	middle = (emp.get("middle_name") or "").ljust(1) or ""

	wages = str(int(emp.get("reportable_wages", 0) * 100)).rjust(17, "0") or ""

	excess = str(int(emp.get("excess_wages", 0) * 100)).rjust(17, "0") or ""

	ach_details = frappe.get_single("ACH Report Details")

	taxing_entity_code = ach_details.taxing_entity_code or ""

	state_unemployment_insurance_account_number = (
		ach_details.state_unemployment_insurance_account_number or ""
	)

	quarter = emp.get("quarter", "")

	quarter = str(emp.get("quarter", "")).strip()

	year = emp.get("print_data")[0]["year"]

	# Map quarter to last month
	quarter_to_month = {"1": "03", "2": "06", "3": "09", "4": "12"}

	month = quarter_to_month.get(quarter, "")
	if not month:
		return ""

	quarter_last_month_year = f"{month}{year}"

	return (
		"S"
		+ pad(ssn, 9)
		+ pad(last_name, 20)
		+ pad(first_name, 12)
		+ pad(middle, 1)
		+ pad("48", 2)
		+ pad("", 18)
		+ pad(wages, 14)
		+ pad("", 14)
		+ pad(excess, 14)
		+ pad("", 37)
		+ pad(taxing_entity_code, 4)
		+ pad(state_unemployment_insurance_account_number, 9)
		+ pad("", 16)
		+ pad("00000", 5)
		+ pad("", 35)
		+ pad(quarter_last_month_year, 6)
	)


def generate_t_record(data):
	def get_month_employee(print_data, index):
		try:
			total = print_data[index].get("total", "") or ""
			return str(total).rjust(7, "0")
		except (IndexError, AttributeError):
			return "".rjust(7, "0")

	total_employees = str(len(data)).rjust(7, "0") or ""

	total_wages = sum(emp.get("reportable_wages", 0) for emp in data)
	total_wages = int(total_wages * 100)  # Convert dollars to cents
	wages = str(total_wages).rjust(14, "0")

	excess_wages = sum(emp.get("excess_wages", 0) for emp in data)

	taxable_wages = sum(emp.get("taxable_wages", 0) for emp in data)
	taxable_wages = int(taxable_wages * 100)  # Convert dollars to cents
	taxable_wages_str = str(taxable_wages).rjust(14, "0")

	contribution_rate = ".013000"
	contribution_amount = int(round(taxable_wages * 0.013))
	contribution_amount_str = str(contribution_amount).rjust(13, "0")

	ach_details = frappe.get_single("ACH Report Details")
	taxing_entity_code = ach_details.taxing_entity_code or ""

	# Safe handling of print_data
	print_data = data[0].get("print_data", []) if data else []

	first_month_employee = get_month_employee(print_data, 0)
	second_month_employee = get_month_employee(print_data, 1)
	third_month_employee = get_month_employee(print_data, 2)

	return (
		"T"
		+ pad(total_employees, 7)
		+ pad(taxing_entity_code, 4)
		+ pad("", 14)
		+ pad(wages, 14)
		+ pad("", 14)
		+ pad(taxable_wages_str, 14)
		+ pad("", 13)
		+ pad(contribution_rate, 6)
		+ pad(contribution_amount_str, 13)
		+ pad("", 126)
		+ pad(first_month_employee, 7)
		+ pad(second_month_employee, 7)
		+ pad(third_month_employee, 7)
		+ pad("RUS", 3)
		+ pad(total_employees, 7)
	)


def generate_f_record(data):
	total_employees = str(len(data)).rjust(10, "0") or ""
	total_employer = "1"
	total_employer = str(total_employer).rjust(10, "0")

	total_wages = sum(emp["reportable_wages"] for emp in data) or ""
	total_wages = int(total_wages * 100)
	total_wages = str(total_wages).rjust(15, "0")

	taxable_wages = sum(emp["taxable_wages"] for emp in data) or ""
	taxable_wages = int(taxable_wages * 100)
	taxable_wages = str(taxable_wages).rjust(15, "0")

	ach_details = frappe.get_single("ACH Report Details")

	taxing_entity_code = ach_details.taxing_entity_code or ""

	return (
		"F"
		+ pad(total_employees, 10)
		+ pad(total_employer, 10)
		+ pad(taxing_entity_code, 4)
		+ pad("", 15)
		+ pad(total_wages, 15)
		+ pad("", 15)
		+ pad(taxable_wages, 15)
	)
