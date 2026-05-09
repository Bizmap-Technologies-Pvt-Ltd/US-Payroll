# Copyright (c) 2026, us_payroll and contributors
# For license information, please see license.txt

from itertools import groupby
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate
from hrms.hr.doctype.leave_allocation.leave_allocation import get_previous_allocation
from hrms.hr.doctype.leave_application.leave_application import (
	get_leave_balance_on,
	get_leaves_for_period,
)
Filters = frappe._dict


def execute(filters: Filters | None = None) -> tuple:
	columns = get_columns()
	data = get_data(filters)
	charts = get_chart_data(data, filters)
	return columns, data, None, charts


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Leave Type"),
			"fieldtype": "Link",
			"fieldname": "leave_type",
			"width": 200,
			"options": "Leave Type",
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "employee_name",
			"width": 200,
			"options": "employee",
		},
		{
			"label": _("Leave Balance"),
			"fieldtype": "float",
			"fieldname": "balance_leaves",
			"width": 200,
		},
		{
			"label": _("Leave Used"),
			"fieldtype": "float",
			"fieldname": "leaves_taken",
			"width": 200,
		}		
	]

def update_leave_data_from_payrol(data,filters):	
	as_of_date = filters.get("as_of_date")
	_data = []

	for row in data:
		if row.get("employee"):
			employee = row.get("employee")
			query = f"""
					SELECT pe.name AS payroll_entry, 
					ped.custom_available_pto, 
					ped.custom_available_ct,
					ped.custom_comp_time,
					ped.custom_pto_hours

					FROM `tabPayroll Entry` pe
					INNER JOIN `tabPayroll Employee Detail` ped ON ped.parent = pe.name
					WHERE ped.employee = '{employee}'
					  AND pe.docstatus = 1
					  AND pe.status != 'Failed'
					  AND pe.posting_date <= '{as_of_date}'					
					"""
			order_by = """ ORDER BY pe.modified DESC """
			condition = " AND 1=1 "

			query += condition + order_by
			past_data = frappe.db.sql(query,as_dict=True)

			if not past_data:
				continue

			row["balance_leaves"] = 0
			row["leaves_taken"] = 0

			if row["leave_type"] == "Comp Time":
				if len(past_data) > 0:
					row["balance_leaves"] = past_data[0].get("custom_available_ct")

					row["leaves_taken"] = sum([_["custom_comp_time"] for _ in past_data ])

			if row["leave_type"] == "PTO":
				if len(past_data) > 0:
					row["balance_leaves"] = past_data[0].get("custom_available_pto")
					row["leaves_taken"] = sum([_["custom_pto_hours"] for _ in past_data ])

			_data.append(row)
		else:
			_data.append(row)			

	return _data


def get_data(filters: Filters) -> list:
	# leave_types = get_leave_types()

	leave_types = ['Comp Time',  'PTO']
	active_employees = get_employees(filters)
	
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
	consolidate_leave_types = len(active_employees) > 1 and filters.consolidate_leave_types
	row = None

	data = []
	for leave_type in leave_types:
		if consolidate_leave_types:
			data.append({"leave_type": leave_type})
		else:
			row = frappe._dict({"leave_type": leave_type})

		for employee in active_employees:
			if consolidate_leave_types:
				row = frappe._dict()
			else:
				row = frappe._dict({"leave_type": leave_type})

			row.employee = employee.name
			row.employee_name = employee.employee_name

			leaves_taken = (
				get_leaves_for_period(employee.name, leave_type, filters.from_date, filters.to_date) * -1
			)

			new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
				filters.from_date, filters.to_date, employee.name, leave_type
			)
			opening = get_opening_balance(employee.name, leave_type, filters, carry_forwarded_leaves)

			row.leaves_allocated = flt(new_allocation, precision)
			row.leaves_expired = flt(expired_leaves, precision)
			row.opening_balance = flt(opening, precision)
			row.leaves_taken = flt(leaves_taken, precision)

			closing = new_allocation + opening - (row.leaves_expired + leaves_taken)
			row.closing_balance = flt(closing, precision)
			row.indent = 1
			row.update({"leave_type":leave_type})
			data.append(row)
	
	data = update_leave_data_from_payrol(data,filters)

	return data


def get_leave_types() -> list[str]:
	LeaveType = frappe.qb.DocType("Leave Type")
	return (frappe.qb.from_(LeaveType).select(LeaveType.name).orderby(LeaveType.name)).run(
		pluck="name"
	)


def get_employees(filters: Filters) -> list[dict]:
	Employee = frappe.qb.DocType("Employee")
	query = frappe.qb.from_(Employee).select(
		Employee.name,
		Employee.employee_name	)

	if filters.get("employee_status"):
		query = query.where(Employee.status == "Active")

	return query.run(as_dict=True)


def get_opening_balance(
	employee: str, leave_type: str, filters: Filters, carry_forwarded_leaves: float
) -> float:
	# allocation boundary condition
	# opening balance is the closing leave balance 1 day before the filter start date
	# opening_balance_date = add_days(filters.from_date, -1)
	opening_balance_date = getdate(add_days(filters.from_date, -1))

	allocation = get_previous_allocation(filters.from_date, leave_type, employee)

	if (
		allocation
		and allocation.get("to_date")
		and opening_balance_date
		and getdate(allocation.get("to_date")) == getdate(opening_balance_date)
	):
		# if opening balance date is same as the previous allocation's expiry
		# then opening balance should only consider carry forwarded leaves
		opening_balance = carry_forwarded_leaves
	else:
		# else directly get leave balance on the previous day
		opening_balance = get_leave_balance_on(employee, leave_type, opening_balance_date)

	return opening_balance


def get_allocated_and_expired_leaves(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> tuple[float, float, float]:
	new_allocation = 0
	expired_leaves = 0
	carry_forwarded_leaves = 0

	records = get_leave_ledger_entries(from_date, to_date, employee, leave_type)

	for record in records:
		# new allocation records with `is_expired=1` are created when leave expires
		# these new records should not be considered, else it leads to negative leave balance
		if record.is_expired:
			continue

		if record.to_date < getdate(to_date):
			# leave allocations ending before to_date, reduce leaves taken within that period
			# since they are already used, they won't expire
			expired_leaves += record.leaves
			leaves_for_period = get_leaves_for_period(
				employee, leave_type, record.from_date, record.to_date
			)
			expired_leaves -= min(abs(leaves_for_period), record.leaves)

		if record.from_date >= getdate(from_date):
			if record.is_carry_forward:
				carry_forwarded_leaves += record.leaves
			else:
				new_allocation += record.leaves

	return new_allocation, expired_leaves, carry_forwarded_leaves


def get_leave_ledger_entries(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> list[dict]:
	ledger = frappe.qb.DocType("Leave Ledger Entry")
	return (
		frappe.qb.from_(ledger)
		.select(
			ledger.employee,
			ledger.leave_type,
			ledger.from_date,
			ledger.to_date,
			ledger.leaves,
			ledger.transaction_name,
			ledger.transaction_type,
			ledger.is_carry_forward,
			ledger.is_expired,
		)
		.where(
			(ledger.docstatus == 1)
			& (ledger.transaction_type == "Leave Allocation")
			& (ledger.employee == employee)
			& (ledger.leave_type == leave_type)
			& (
				(ledger.from_date[from_date:to_date])
				| (ledger.to_date[from_date:to_date])
				| ((ledger.from_date < from_date) & (ledger.to_date > to_date))
			)
		)
	).run(as_dict=True)


def get_chart_data(data: list, filters: Filters) -> dict:
	labels = []
	datasets = []
	employee_data = data

	if not data:
		return None

	if data and filters.employee:
		get_dataset_for_chart(employee_data, datasets, labels)

	chart = {
		"data": {"labels": labels, "datasets": datasets},
		"type": "bar",
		"colors": ["#456789", "#EE8888", "#7E77BF"],
	}

	return chart


def get_dataset_for_chart(employee_data: list, datasets: list, labels: list) -> list:
	leaves = []
	employee_data = sorted(employee_data, key=lambda k: k["employee_name"])

	for key, group in groupby(employee_data, lambda x: x["employee_name"]):
		for grp in group:
			if grp.closing_balance:
				leaves.append(
					frappe._dict({"leave_type": grp.leave_type, "closing_balance": grp.closing_balance})
				)

		if leaves:
			labels.append(key)

	for leave in leaves:
		datasets.append({"name": leave.leave_type, "values": [leave.closing_balance]})
