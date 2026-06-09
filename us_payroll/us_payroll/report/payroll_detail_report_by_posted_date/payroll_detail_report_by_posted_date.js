// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

/* globals erpnext */

frappe.query_reports["Payroll Detail Report By Posted Date"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: get_date().fromDate,
			width: 80,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: get_date().toDate,
			width: 80,
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			width: 80,
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			width: 80,
			hidden: 1,
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Print"), function () {
			frappe.call({
				method: "us_payroll.us_payroll.report.payroll_detail_report_by_posted_date.payroll_detail_report_by_posted_date.get_print",
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
					link.download = "payroll_detail_report" + timestamp + ".pdf";
					link.click();
				},
			});
		});
	},
};

function get_date() {
	let today = new Date();
	let currentYear = today.getFullYear();

	let fromDateStr = `01/01/${currentYear}`;
	let fromDate = new Date(fromDateStr);
	let toDate = new Date();

	return { fromDate, toDate };
}
