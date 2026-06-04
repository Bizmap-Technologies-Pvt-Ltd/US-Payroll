import datetime
import io
import math
from calendar import monthrange
from datetime import datetime

import frappe
from frappe.utils.file_manager import save_file

from us_payroll.us_payroll.report.tmrs_report import tmrs_report


@frappe.whitelist()
def get_tmrs_report_data(year, month):
	# Convert input
	year = int(year)
	month_names = [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December",
	]
	current_month_index = month_names.index(month)

	# Determine previous month and year
	if current_month_index == 0:
		prev_month = 12
		prev_year = year - 1
	else:
		prev_month = current_month_index
		prev_year = year

	start_date = datetime.date(prev_year, prev_month, 1)
	end_date = datetime.date(prev_year, prev_month, monthrange(prev_year, prev_month)[1])

	filters = {"year": year, "month": month}

	columns, sample_data = tmrs_report.execute(filters)

	# Build lines
	ach_lines = []
	for row in sample_data:
		city_number = "00962"
		ssn = f'{row["custom_nomasked_social_security_number"]:<9}'.replace("-", "")
		salary = f'{int(row["gross_pay"] * 100):08}'  # 8 digits, cents
		deposit = f'{int(row["tmrs_employee_total"] * 100):07}'  # 7 digits, cents

		# name = f'{row["employee"]:<33}'[:33]  # limit to 33 characters

		name = format_emp_name(row.get("first_name"), row.get("middle_name"), row.get("last_name"))

		file_row = f"{city_number}{ssn}{salary}{deposit}{name}"
		ach_lines.append(file_row)

	# Save the file
	file_name = f"ACH_{start_date.strftime('%Y_%m')}.txt"
	file_content = "\n".join(ach_lines)  # ✅ join rows, not characters

	file_doc = save_file(
		fname=file_name, content=file_content, dt=None, dn=None, folder="Home/Attachments", is_private=1
	)

	return {"file_url": file_doc.file_url}


def format_emp_name(first, middle, last):
	# Capitalize & strip fields
	first = (first or "").strip().title()
	middle = (middle or "").strip()
	last = (last or "").strip().title()

	# Middle initial if exists
	middle_initial = f"{middle[0].upper()}." if middle else ""

	# Combine into preferred format: Last, First M.
	full_name = f"{last}, {first} {middle_initial}".strip()

	# Pad/truncate to 33 characters for fixed-width
	return full_name[:33].ljust(33)
