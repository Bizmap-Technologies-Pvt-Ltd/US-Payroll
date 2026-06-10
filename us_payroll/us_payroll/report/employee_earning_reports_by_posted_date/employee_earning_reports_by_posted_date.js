// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Earning Reports By Posted Date"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("Start Date"),
			fieldtype: "Date",
			default: new Date().getFullYear() + "-01-01",
			reqd: 1,
			width: "100px",
		},
		{
			fieldname: "to_date",
			label: __("End Date"),
			fieldtype: "Date",
			default: new Date().getFullYear() + "-01-31",
			reqd: 1,
			width: "100px",
		},
		{
			fieldname: "year",
			fieldtype: "Link",
			options: "Year",
			reqd: 1,
			default: new Date().getFullYear().toString(),
			label: __("Year"),
			on_change: function (query_report) {
				let year = frappe.query_report.get_filter_value("year");
				if (year) {
					frappe.query_report.set_filter_value("from_date", year + "-01-01");
					frappe.query_report.set_filter_value("to_date", year + "-01-31");
				}
			},
		},
	],

	onload: function (report) {},
};
