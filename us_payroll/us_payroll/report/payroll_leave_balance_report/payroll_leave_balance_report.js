// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.query_reports["Payroll Leave Balance Report"] = {
	filters: [
		{
			"fieldname": "as_of_date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.now_date(),
			"width": 80,
		},
		{
			fieldname: "consolidate_leave_types",
			label: __("Consolidate Leave Types"),
			fieldtype: "Check",
			default: 1,
			// depends_on: "eval: !doc.employee",
			hidden: 1
		}
	],
	onload: () => {
		const today = frappe.datetime.now_date();

	}
}
