// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.query_reports["Workers' Comp Report"] = {
	"filters": [ 
		{ 
			"fieldname": "from_date", 
			"label": "From Date", 
			"fieldtype": "Date", 
			"default": (new Date()).getFullYear() + "-10-01", 
			"reqd": 1 
		}, 
		{
			"fieldname": "to_date", 
			"label": "To Date", 
			"fieldtype": "Date", 
			"default": (new Date()).getFullYear(), 
			"reqd": 1 
		}, 
	],

	onload: function(report) {
		report.page.add_inner_button(__("Print"), function () {
	        frappe.call({
	            method: "us_payroll.us_payroll.report.workers'_comp_report.workers'_comp_report.get_print",
	            args: {
	                report_data: {'filter': report.get_values(), 'data': report.data,},
	            },
	            callback: function(response) {
	                var response_data = response.message.pdf_file;
	                var bytes = new Uint8Array(response_data);
	                var blob = new Blob([bytes], {type: 'application/octet-stream'});
	                var link = document.createElement("a");
	                link.href = window.URL.createObjectURL(blob);
	                var now = new Date();
	                var timestamp = now.toISOString().slice(0, 19).replace(/[-T]/g, '').replace(/:/g, '');
	                link.download = "workers_comp_report" + timestamp + ".pdf";
	                link.click();
	            }
	        });
	    });
	},
};
