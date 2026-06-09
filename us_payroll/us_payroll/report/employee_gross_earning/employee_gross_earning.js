// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Gross Earning"] = {
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

	onload: function (report) {
		report.page.add_inner_button(__("Print"), function () {
			frappe.call({
				method: "us_payroll.us_payroll.report.employee_gross_earning.employee_gross_earning.get_print",
				args: {
					report_data: { filter: report.get_values(), data: report.data },
				},
				callback: function (response) {
					var response_data = response.message.pdf_file;
					var bytes = new Uint8Array(response_data);
					var blob = new Blob([bytes], { type: "application/octet-stream" });
					var link = document.createElement("a");
					link.href = window.URL.createObjectURL(blob);
					var now = new Date();
					var timestamp = now
						.toISOString()
						.slice(0, 19)
						.replace(/[-T]/g, "")
						.replace(/:/g, "");
					link.download = "employee_gross_earning" + timestamp + ".pdf";
					link.click();
				},
			});
		});
	},
};
