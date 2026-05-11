// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.query_reports["Payroll Employee Taxes"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(),-1),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname":"to_date",
			"label": __("To"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"label": __("Department"),
			"width": "50px"
		},
		
	]
};

