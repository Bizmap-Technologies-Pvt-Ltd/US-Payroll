// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.query_reports["TMRS Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company"),
			"hidden": 1
		},
		{
			"fieldname": "year",
			"fieldtype": "Link",
			"options": "Year",
			"reqd": 1,
			"default": (new Date()).getFullYear().toString(),
			"label": __("Year"),
		},	
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
		},
	],

	onload: function(report) {
		report.page.add_inner_button(__("Print"), function () {
	        frappe.call({
	            method: 'us_payroll.us_payroll.report.tmrs_report.tmrs_report.get_print',
	            args: {
	                report_data: {'filter': report.get_values(), 'data': report.data},
	            },
	            callback: function(response) {
	                var response_data = response.message.pdf_file;
	                var bytes = new Uint8Array(response_data);
	                var blob = new Blob([bytes], {type: 'application/octet-stream'});
	                var link = document.createElement("a");
	                link.href = window.URL.createObjectURL(blob);
	                var now = new Date();
	                var timestamp = now.toISOString().slice(0, 19).replace(/[-T]/g, '').replace(/:/g, '');
	                link.download = "tmrs_report" + timestamp + ".pdf";
	                link.click();
	            }
	        });
	    });
	},
};
