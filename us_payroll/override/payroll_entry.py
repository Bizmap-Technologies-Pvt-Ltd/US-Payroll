# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
import json

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import (
	DATE_FORMAT,
	add_days,
	add_months,
	add_to_date,
	cint,
	comma_and,
	date_diff,
	flt,
	get_first_day,
	get_last_day,
	get_link_to_form,
	getdate,
	now_datetime,
	rounded,
	today,
)
from hrms.hr.doctype.leave_application.leave_application import get_leave_details
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry, get_month_details


class OverridePayrollEntry(PayrollEntry):
	def validate(self):
		super().validate()
		self.validate_business_rules()
		self.calculate_time_data()
		self.validate_leave_rules()

	def before_submit(self):
		super().before_submit()
		self.warning_msg()

	def on_submit(self):
		super().on_submit()

	@frappe.whitelist(methods=["POST"])
	def create_salary_slips(self):
		add_check_employees = []

		for row in self.employees:
			employee_payment_method = frappe.db.get_value(
				"Employee",
				row.employee,
				"custom_payment_method",
			)

			if employee_payment_method == "Check":
				add_check_employees.append(row.employee)

		available_check = frappe.get_all(
			"Check",
			filters={"status": "Available"},
			fields=["name", "check_number"],
			order_by="check_number ASC",
		)

		if len(available_check) < len(add_check_employees):
			frappe.throw(_("Number of available checks are less than the required."))

		return super().create_salary_slips()

	def get_insurance_details_from_ssa(self, employee, salary_component):
		ssa = frappe.db.get_value(
			"Salary Structure Assignment", {"employee": employee, "docstatus": 1}, "name"
		)
		if not ssa:
			return None, None

		result = frappe.db.get_value(
			"Employee Insurance Deduction",
			{"parent": ssa, "salary_component": salary_component},
			["insurance_company", "salary_component"],
		)
		if not result:
			return None, None

		return result

	def get_insurance_provider_account(self, provider):
		provider_doc = frappe.get_cached_doc("Insurance Provider", provider)

		for row in provider_doc.accounts:
			if row.account:
				return row.account

		frappe.throw(_("Please set proper Insurance account in Insurance Provider {0}").format(provider))

	def get_salary_component_account(self, salary_component, employee=None):
		comp_doc = frappe.get_cached_doc(
			"Salary Component",
			salary_component,
		)

		if comp_doc.type == "Deduction" and (
			comp_doc.custom_is_this_insurance_component
			or comp_doc.custom_is_this_employers_insurance_component
		):
			provider, _ = self.get_insurance_details_from_ssa(
				employee,
				salary_component,
			)

			if provider:
				return self.get_insurance_provider_account(provider)

		return super().get_salary_component_account(
			salary_component,
		)

	def get_salary_component_total(
		self,
		component_type=None,
		employee_wise_accounting_enabled=False,
	):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}

			for item in salary_components:
				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
					item.employee, item.salary_structure
				)
				employee_advance = self.get_advance_deduction(component_type, item)

				for cost_center, percentage in employee_cost_centers.items():
					amount_against_cost_center = flt(item.amount) * percentage / 100

					if employee_advance:
						self.add_advance_deduction_entry(
							item, amount_against_cost_center, cost_center, employee_advance
						)
					else:
						employee = item.employee
						key = (item.salary_component, cost_center, employee)
						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center

					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(
							component_type, item.employee, amount_against_cost_center
						)

			account_details = self.get_account(component_dict=component_dict)

			return account_details

	def get_account(self, component_dict=None, employee=None):
		account_dict = {}
		for key, amount in component_dict.items():
			component, cost_center, employee = key
			account = self.get_salary_component_account(component, employee)
			accounting_key = (account, cost_center)
			account_dict[accounting_key] = account_dict.get(accounting_key, 0) + amount
		return account_dict

	def make_accrual_jv_entry(self, submitted_salary_slips):
		self.employee_check_map = self.get_employee_check_numbers(submitted_salary_slips)

		return super().make_accrual_jv_entry(submitted_salary_slips)

	def get_employee_check_numbers(self, submitted_salary_slips):
		employee_check_map = {}
		if not submitted_salary_slips:
			return employee_check_map

		salary_slip_names = []
		for slip in submitted_salary_slips:
			if isinstance(slip, str):
				salary_slip_names.append(slip)
			else:
				salary_slip_names.append(slip.name)

		salary_slips = frappe.get_all(
			"Salary Slip",
			filters={
				"name": ["in", salary_slip_names],
			},
			fields=["employee", "custom_check_no"],
		)
		for slip in salary_slips:
			if slip.custom_check_no:
				employee_check_map[slip.employee] = slip.custom_check_no

		return employee_check_map

	def update_check_number_remark(self, accounts):
		employee_check_map = getattr(self, "employee_check_map", {})
		for row in accounts:
			employee = row.get("party")

			if employee and employee in employee_check_map:
				row["user_remark"] = employee_check_map[employee]

	def make_journal_entry(self, *args, **kwargs):
		accounts = kwargs.get("accounts")

		if accounts is None and args:
			accounts = args[0]

		if accounts:
			self.update_check_number_remark(accounts)

		return super().make_journal_entry(*args, **kwargs)

	def validate_business_rules(self):
		self.insurance_deduction_limitation()
		self.validate_do_not_include_in_total()
		self.validate_ssa_do_not_include_in_total()

	def calculate_time_data(self):
		self.calculate_working_hours()
		self.calculate_holiday_hours()

	def validate_leave_rules(self):
		self.get_leave_balance()
		self.carry_forward()

	def carry_forward(self):
		doc = self
		for row in doc.employees:
			if not row.custom_pto_hours:
				self.process_pto_leave_balance_and_carry_forward()

	def warning_msg(self):
		doc = self
		for row in doc.employees:
			total_hours = float(row.custom_total_working_hours or 0)
			overtime = float(row.custom_total_overtime_hours or 0)
			comp_time = float(row.custom_comp_time or 0)
			pto = float(row.custom_pto_hours or 0)
			holiday = float(row.custom_holiday_hours or 0)
			base_amount = float(row.custom_base_amount or 0)

			if (
				total_hours == 0
				and overtime == 0
				and comp_time == 0
				and pto == 0
				and holiday == 0
				and base_amount == 0
			):
				frappe.throw(
					f"Row <b>{row.idx}</b> for employee <b>{row.employee_name}</b> "
					"has zero hours entered in all categories: "
					"<b>Hourly, Overtime, Comp Time, PTO, Holiday and Base Amount</b>. "
					"Please enter hours to proceed."
				)

	def insurance_deduction_limitation(self):
		doc = self
		if not doc.custom_deduct_insurance:
			fy_current = self.get_us_fiscal_year(date_value=doc.posting_date)
			current_fiscal_year = fy_current["fiscal_year"]
			fiscal_year_start = fy_current["fiscal_year_start"]
			fiscal_year_end = fy_current["fiscal_year_end"]

			if not current_fiscal_year:
				frappe.throw(_("Fiscal Year not found for posting date {0}").format(doc.posting_date))

			for d in doc.employees:
				employee = d.employee
				emp_name = d.employee_name
				row = d.idx

				count = frappe.db.sql(
					"""
					SELECT COUNT(pe.name)
					FROM `tabPayroll Entry` pe
					INNER JOIN `tabPayroll Employee Detail` child
						ON child.parent = pe.name
					WHERE pe.docstatus = 1
					  AND pe.custom_deduct_insurance = 0
					  AND child.employee = %s
					  AND pe.posting_date BETWEEN %s AND %s
				""",
					(employee, fiscal_year_start, fiscal_year_end),
				)[0][0]

				if count >= 2:
					frappe.throw(
						_(
							f"Please remove employee <b>{emp_name}</b> from row <b>{row}</b>, as for this employee the insurance deduction has already been skipped twice in this fiscal year."
						)
					)

	def validate_do_not_include_in_total(self):
		doc = self
		salary_components = frappe.get_all(
			"Salary Component", filters={"custom_is_this_insurance_component": True}, fields=["name"]
		)
		for sc in salary_components:
			sal_doc = frappe.get_doc("Salary Component", sc.name)
			if (
				doc.custom_deduct_insurance
				and sal_doc.custom_is_this_insurance_component
				and sal_doc.do_not_include_in_total
			):
				sal_doc.do_not_include_in_total = False
				sal_doc.save(ignore_permissions=True)

	def validate_ssa_do_not_include_in_total(self):
		doc = self
		for emp_row in doc.employees:
			ssa_name = frappe.db.get_value(
				"Salary Structure Assignment",
				filters={"employee": emp_row.employee, "docstatus": 1},
				fieldname="name",
			)
			if not ssa_name:
				frappe.throw(f"No Salary Structure Assignment found for employee {emp_row.employee}")

			ssa_doc = frappe.get_doc("Salary Structure Assignment", ssa_name)
			for ins_row in ssa_doc.custom_employee_insurance_deduction:
				if (
					doc.custom_deduct_insurance
					and ins_row.is_this_employees_insurance_component
					and ins_row.do_not_include_in_total
				):
					ins_row.do_not_include_in_total = 0
			ssa_doc.save(ignore_permissions=True)

	def get_leave_balance(self):
		payroll_doc = self
		for row in payroll_doc.employees:
			# ----------------Comp time calculation------------
			leave_allocation_data = frappe.db.get_values(
				"Leave Allocation",
				{"employee": row.employee, "leave_type": "Comp Time", "docstatus": 1},
				["name", "from_date", "total_leaves_allocated"],
				as_dict=1,
			)

			from frappe.utils import get_url

			site_url = get_url()
			leave_allocation_url = f"{site_url}/app/leave-allocation"

			if row.custom_comp_time > 0 and not leave_allocation_data:
				frappe.throw(
					f"Please allocate CT Leaves for employee <b>{row.employee_name}</b> in row <b>{row.get('idx')}</b> <a href= '{leave_allocation_url}' > Leave Allocation </a>"
				)

			total_comp_leaves_allocated = 0
			if leave_allocation_data:
				leave_allocation_data = leave_allocation_data[0]
				leave_allocation_from_date = leave_allocation_data.get("from_date")
				total_comp_leaves_allocated = leave_allocation_data.get("total_leaves_allocated")
				leave_application_leave_details = get_leave_details(row.employee, leave_allocation_from_date)

			payrol_entry_data = frappe.db.sql(
				"""
								SELECT SUM(pd.custom_comp_time) as total_cmp_leaves
								FROM `tabPayroll Employee Detail` pd
								LEFT JOIN `tabPayroll Entry` pe ON pd.parent = pe.name
								WHERE pe.docstatus = 1 AND pd.employee = %s
							""",
				(row.employee,),
				as_dict=True,
			)

			total_cmp_leaves_from_payroll = 0
			if payrol_entry_data:
				payrol_entry_data = payrol_entry_data[0]
				total_cmp_leaves_from_payroll = payrol_entry_data.get("total_cmp_leaves") or 0
				if total_cmp_leaves_from_payroll:
					total_cmp_leaves_from_payroll = total_cmp_leaves_from_payroll

			if row.custom_comp_time and total_comp_leaves_allocated:
				custom_comp_time = row.custom_comp_time
				total_cmp_leaves = custom_comp_time + total_cmp_leaves_from_payroll
				leave_application_comp_leaves_taken = leave_application_leave_details["leave_allocation"][
					"Comp Time"
				]["leaves_taken"]
				total_ct_available_leaves = (
					total_comp_leaves_allocated - total_cmp_leaves + leave_application_comp_leaves_taken
				)
				if (total_cmp_leaves + leave_application_comp_leaves_taken) <= total_comp_leaves_allocated:
					row.custom_available_ct = total_ct_available_leaves

				if (total_cmp_leaves + leave_application_comp_leaves_taken) > total_comp_leaves_allocated:
					frappe.throw(
						f"Comp Time leaves cannot be more than allocated leaves for employee <b>{row.employee_name}</b> in row <b>{row.get('idx')}</b>."
					)

			elif not row.custom_comp_time and total_comp_leaves_allocated:
				row.custom_available_ct = total_comp_leaves_allocated - total_cmp_leaves_from_payroll

			elif not row.custom_comp_time and not total_comp_leaves_allocated:
				pass

			else:
				pass

	def get_us_fiscal_year(self, date_value=None):
		if not date_value:
			date_value = now_datetime().date()
		else:
			date_value = getdate(date_value)

		year = date_value.year
		if date_value.month < 10:
			start_year = year - 1
			end_year = year
		else:
			start_year = year
			end_year = year + 1

		fiscal_year_start = getdate(f"{start_year}-10-01")
		fiscal_year_end = getdate(f"{end_year}-09-30")

		return {
			"fiscal_year": f"{start_year}-{end_year}",
			"fiscal_year_start": fiscal_year_start,
			"fiscal_year_end": fiscal_year_end,
		}

	def process_pto_leave_balance_and_carry_forward(self):
		payroll_doc = self
		fy_current = self.get_us_fiscal_year(date_value=payroll_doc.start_date)
		fiscal_year_start = fy_current["fiscal_year_start"]
		fiscal_year_end = fy_current["fiscal_year_end"]

		for row in payroll_doc.employees:
			employee = row.employee
			leave_alloc = frappe.db.get_value(
				"Leave Allocation",
				{
					"employee": employee,
					"leave_type": "PTO",
					"docstatus": 1,
					"from_date": [">=", fiscal_year_start],
					"to_date": ["<=", fiscal_year_end],
				},
				["name", "from_date", "to_date", "total_leaves_allocated", "modified"],
				as_dict=True,
			)
			total_leaves_allocated_pto = flt(leave_alloc.total_leaves_allocated) if leave_alloc else 0
			emp = frappe.db.get_value("Employee", employee, ["custom_pto_hours"], as_dict=True)
			pto_rate = flt(emp.custom_pto_hours) if emp else 0

			# Get last payroll's cumulative accrual (if exists)
			last_accrual = frappe.db.sql(
				"""
				SELECT ped.custom_total_accrual_pto
				FROM `tabPayroll Entry` pe
				INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
				WHERE ped.employee = %s
				  AND pe.docstatus = 1
				  AND pe.start_date >= %s
				  AND pe.start_date <= %s
				ORDER BY pe.start_date DESC
				LIMIT 1
			""",
				(employee, fiscal_year_start, fiscal_year_end),
				as_dict=True,
			)

			prev_total_accrual = flt(last_accrual[0].custom_total_accrual_pto) if last_accrual else 0

			# Add current pto_rate to running total
			row.custom_total_accrual_pto = prev_total_accrual + pto_rate

			past_pto = frappe.db.sql(
				"""
				SELECT pe.name AS payroll_entry, ped.custom_available_pto, ped.custom_pto_leaves_allocated
				FROM `tabPayroll Entry` pe
				INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
				WHERE ped.employee = %s
				  AND pe.docstatus = 1
				  AND pe.start_date >= %s
				  AND pe.start_date <= %s
				ORDER BY pe.start_date DESC
				LIMIT 1
			""",
				(employee, fiscal_year_start, fiscal_year_end),
				as_dict=True,
			)

			cumulative_pto = flt(past_pto[0].custom_available_pto) if past_pto else 0
			past_alloc_used = (
				flt(past_pto[0].custom_pto_leaves_allocated)
				if past_pto and past_pto[0].custom_pto_leaves_allocated
				else 0
			)

			new_pto_balance = cumulative_pto + pto_rate
			delta_allocation = (total_leaves_allocated_pto - past_alloc_used) if leave_alloc else 0

			row.custom_available_pto = new_pto_balance + delta_allocation
			row.custom_pto_leaves_allocated = total_leaves_allocated_pto

			# --------------------------------    CARRY FORWARD Logic  --------------------------------------------------
			# Check if this is the first payroll for the fiscal year for this employee
			first_payroll_in_fy = not frappe.db.exists(
				"Payroll Employee Detail",
				{
					"employee": employee,
					"parenttype": "Payroll Entry",
					"start_date": ["between", [fiscal_year_start, fiscal_year_end]],
				},
			)

			if first_payroll_in_fy:
				already_carry_forwarded = frappe.db.sql(
					"""
					SELECT ped.name
					FROM `tabPayroll Employee Detail` ped
					INNER JOIN `tabPayroll Entry` pe ON pe.name = ped.parent
					WHERE ped.employee = %s
					  AND pe.docstatus = 1
					  AND pe.start_date BETWEEN %s AND %s
					  AND IFNULL(ped.custom_pto_carry_applied, 0) = 1
					LIMIT 1
				""",
					(employee, fiscal_year_start, fiscal_year_end),
					as_dict=True,
				)

			# row.custom_pto_carry_applied = False
			if first_payroll_in_fy and not already_carry_forwarded:
				# Get the last payroll from previous fiscal year
				prev_payroll = frappe.db.sql(
					"""
					SELECT pe.name, ped.custom_available_pto
					FROM `tabPayroll Entry` pe
					INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
					WHERE ped.employee = %s
					AND pe.docstatus = 1
					AND pe.start_date < %s
					ORDER BY pe.end_date DESC
					LIMIT 1
				""",
					(employee, fiscal_year_start),
					as_dict=True,
				)

				leave_type = frappe.db.get_value(
					"Leave Type",
					{"name": "PTO"},
					["custom_is_accrual_rate", "custom_carry_forward_hours"],
					as_dict=True,
				)

				if prev_payroll and leave_type and leave_type.custom_is_accrual_rate:
					carry_limit = flt(leave_type.custom_carry_forward_hours)
					prev_balance = flt(prev_payroll[0].custom_available_pto)
					carry_forward_amount = min(prev_balance, carry_limit)

					if carry_forward_amount > 0:
						row.custom_available_pto += carry_forward_amount
						row.custom_carry_forward_pto = carry_forward_amount
						row.custom_pto_carry_applied = True

		return payroll_doc

	def calculate_holiday_hours(self):
		doc = self
		start_date = doc.get("start_date")
		end_date = doc.get("end_date")

		if not start_date or not end_date:
			frappe.throw(_("Please select both Start Date and End Date."))

		start_date = getdate(start_date)
		end_date = getdate(end_date)

		holiday_list = frappe.db.get_value(
			"Company", frappe.defaults.get_global_default("company"), "default_holiday_list"
		)

		if not holiday_list:
			frappe.throw(_("No holiday list found for the company."))

		holidays = frappe.db.sql(
			"""
			SELECT holiday_date, description FROM `tabHoliday`
			WHERE parent=%s AND holiday_date BETWEEN %s AND %s
			ORDER BY holiday_date ASC
		""",
			(holiday_list, start_date, end_date),
			as_dict=True,
		)

		# **Filter out Saturdays and Sundays**
		filtered_holidays = [
			holiday
			for holiday in holidays
			if holiday.holiday_date.weekday() not in (5, 6)  # 5 = Saturday, 6 = Sunday
		]

		total_holiday_hours = len(filtered_holidays) * 8  # Each holiday = 8 hours
		if doc.get("employees"):
			for row in doc.get("employees"):
				if row.custom_holiday_hours and row.custom_holiday_hours != total_holiday_hours:
					row.custom_holiday_amount = (row.custom_hourly_rate or 0) * row.custom_holiday_hours
					continue

				if total_holiday_hours and row.custom_holiday_hours == 0:
					row.custom_holiday_amount = (row.custom_hourly_rate or 0) * row.custom_holiday_hours
					continue

				row.custom_holiday_hours = total_holiday_hours
				row.custom_holiday_amount = (row.custom_hourly_rate or 0) * total_holiday_hours
		# doc.save(ignore_permissions=True)

	def calculate_working_hours(doc):
		for row in doc.employees:
			if not row.custom_total_working_hours:
				total_hours, overtime_hours = frappe.db.sql(
					"""
					SELECT SUM(custom_total_working_hours), SUM(custom_overtime_hours)
					FROM `tabAttendance`
					WHERE employee = %s
					AND attendance_date BETWEEN %s AND %s
					AND status IN ('Present', 'Half Day', 'Work From Home')
					AND docstatus = 1
				""",
					(row.employee, doc.start_date, doc.end_date),
				)[0]

				row.custom_total_working_hours = total_hours or 0
				row.custom_total_overtime_hours = overtime_hours or 0
