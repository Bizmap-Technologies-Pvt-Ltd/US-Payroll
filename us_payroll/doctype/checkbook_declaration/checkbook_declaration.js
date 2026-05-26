// Copyright (c) 2026, us_payroll and contributors
// For license information, please see license.txt

frappe.ui.form.on("Checkbook Declaration", {
	refresh: function(frm){
	
	},

	onload: function(frm){
		
	},

	validate: function(frm){

	},

	first_check_number: function(frm){
		first_check_number = frm.doc.first_check_number 	
		if (isNaN(Number(first_check_number))) {
			frm.set_value("first_check_number", " ")
			frappe.throw("First Check Number is not valid. Please enter integer only.")
		}
	},

	no_of_leaves: function(frm){
		no_of_leaves = frm.doc.no_of_leaves 	
		if (isNaN(Number(no_of_leaves))) {
			frm.set_value("no_of_leaves", " ")
			frappe.throw("Number of leaves is not valid. Please enter integer only.")
		}
	},

	create_all_checks: function(frm) {
		frappe.call({
			method: 'us_payroll.us_payroll.doctype.checkbook_declaration.checkbook_declaration.generate_checks',
			args: {
				docname: frm.doc.name
			},
			freeze: true,
			freeze_message: __("Generating checks...."),
			callback: function(r) {
				frappe.msgprint("Checks generated successfully.")
				if (r.message) {
					frappe.show_alert({
						message: __('Checks generated successfully'),
						indicator: 'green'
					});
					frm.reload_doc();
				}
			}
		});
	}
	 
});
