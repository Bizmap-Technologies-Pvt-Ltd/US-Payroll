// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.page.sidebar.toggle();

frappe.ui.form.on('Payroll Entry', {
	
	refresh: function (frm) {
		// Remove core Submit Salary Slips button
		frm.remove_custom_button(__("Submit Salary Slip"));

		// Add our own non-freezing button
		if (frm.doc.docstatus === 1 && !frm.doc.salary_slips_submitted) {
			frm.add_custom_button(
				__("Submit Salary"),
				() => submit_salary_slip_no_freeze(frm)
			).addClass("btn-primary");
		}

		frm.trigger("set_default_company");
		frm.trigger("set_total_amount");	
		frm.trigger("change_button_label");
		frm.trigger("payment_account_adjustment");
		frm.trigger('hide_add_row_btn'); 
		frm.trigger("make_dashboard")
		frm.trigger('void_check');
		
		if (frm.doc.docstatus == 1) {
			frm.events.add_print_checks_buttons(frm);
			frm.events.add_payroll_ach_button(frm);
		}
	},

	onload: function (frm) {
		frm.trigger("set_default_company");
       	frm.trigger("set_total_amount");
       	frm.trigger("change_button_label");
       	frm.trigger("payment_account_adjustment");
       	frm.trigger('hide_add_row_btn');
		frm.trigger('void_check');

		frm.fields_dict['employees'].grid.wrapper.on('grid-rows-rendered', function () {
			frm.trigger('hide_add_row_btn');
		});
		frm.set_value('exchange_rate', 1.0);
		
    },

    validate:function(frm){
		frm.trigger("set_default_company");		
	},

	hide_add_row_btn: function(frm) {
		frm.fields_dict['employees'].grid.wrapper.find('.grid-add-row').remove();
	},

	start_date: function (frm) {
		if (!in_progress && frm.doc.start_date) {
			frm.trigger("set_end_date");
		} else {
			in_progress = false;
		}
		frm.events.clear_employee_table(frm);
	},

	set_end_date: function (frm) {
		frappe.call({
			method: "us_payroll.custom_script.payroll_entry.get_end_date",
			args: {
				frequency: frm.doc.payroll_frequency,
				start_date: frm.doc.start_date,
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("end_date", r.message.end_date);
				}
			},
		});
	},


    set_default_company:function(frm){
    	if (frm.doc.__islocal == 1) {
	        frappe.call({
	            method: 'us_payroll.custom_script.payroll_entry.get_global_defaults_values',
	            args: {
	                doctype: "Global Defaults",	                
	            },
	            callback: function(r) {
	                if (r.message) {	                   
	                    default_company = r.message.company
	                    frm.set_value('company', default_company);
	                }
	            }
	        });
	    }
    },

    set_total_amount: function (frm) {
    	if(frm.doc.employees.length > 0 && frm.doc.docstatus == 0){
			frm.add_custom_button(__("Set Total Amount"),
					function() {
						frm.events.get_total_amount(frm);
					}
			).css({"background":"#BDCDF3"});
		}
    },

    make_check_entry: function (frm) {
    	frappe.call({
	        method: "us_payroll.custom_script.payroll_entry.get_bank_entry_against_payroll",
	        args:{ 
	        		"doc_id": frm.doc.name,
	        	 },
	        callback: function (r) {
	            if (r.message) {
	                var bank_entry_jv = r.message.bank_entry_jv;
	                var check_entry_jv = r.message.check_entry_jv;
	                if (bank_entry_jv && bank_entry_jv.length > 0 && check_entry_jv.length == 0) {
	                	frm.add_custom_button(__("Make Check Entry"),
							function() {
								check_entry(frm);
							}
					).addClass("btn-primary");

	                }
	                 else {
                        frm.remove_custom_button("Make Check Entry");
                    }
	            }            	            
            },
        });
    },

    change_button_label: function (frm) { 
        $('.page-head-content').find('[data-label="Submit%20Salary%20Slip"]').text("Submit Salary");	
	},

    payment_account_adjustment: function (frm) {
        frappe.call({
            method: "us_payroll.custom_script.payroll_entry.get_account_options",
            callback: function(r) {
                if (r.message) {
                    let options = r.message;                  
                    // Set the first value as the default value
                    if (options && options.length > 0 && frm.doc.__islocal == 1) {
                        frm.set_value('payment_account', options[0]);
                    }
                }
            }
        });
    },

	get_total_amount: function (frm) {
        frappe.call({
            method: "us_payroll.custom_script.payroll_entry.calculate_employee_totals",
            args:{ 
            		"doc": frm.doc,
            		"start_date": frm.doc.start_date,
            		"end_date": frm.doc.end_date
            	 },
            callback: function (r) {
                var employee_totals = r.message.employee_totals;
	            frm.doc.employees.forEach(function(employee) {
	                var employee_id = employee.employee;
	                if (employee_id && employee_totals[employee_id]) {
	                    frappe.model.set_value(employee.doctype, employee.name, 'custom_total_amount', employee_totals[employee_id]['custom_total_amount']);
	                    frappe.model.set_value(employee.doctype, employee.name, 'custom_total_overtime_amount', employee_totals[employee_id]['overtime_amount']);
	                                    
	                    cur_frm.fields_dict['employees'].grid.get_field('custom_total_working_hours').get_query = function(doc, cdt, cdn) {
	                        return { read_only: 1 };
	                    };
	                    cur_frm.fields_dict['employees'].grid.get_field('custom_total_overtime_hours').get_query = function(doc, cdt, cdn) {
	                        return { read_only: 1 };
	                    };                  
	                }
	            });
	            
	            frm.refresh();
            	frm.save();                
                },
            });   
    },

	start_date: function(frm) {
		frm.trigger("make_dashboard")
	},
	
	end_date:function(frm){
		frm.trigger("make_dashboard")
	},

	add_payroll_ach_button: function (frm) {
		if (frm.doc.salary_slips_created && frm.doc.status !== "Queued") {
			frappe.call({
				method: 'us_payroll.custom_script.payroll_entry.get_submitted_check_stubs',
				args: {
					'doc_id': frm.doc.name
				},
				async: false, 
				callback: function(r) {
					var submitted_entries = r.message.submitted_entries;
					if (submitted_entries.length == 0) {
						frm.remove_custom_button("Payroll ACH");          
					} else {

						if (!frm.custom_buttons["Payroll ACH"]) {
							frm.add_custom_button(__("Payroll ACH"), function () {
								frappe.call({
									method: "us_payroll.custom_script.payroll_entry.get_employees_with_bank_payment",
									args: { doc_id: frm.doc.name },
									callback: function (r) {
										if (r.message && r.message.length > 0) {
											console.log("Payroll ACH");
											frm.trigger('redirection'); // Trigger only if bank entries exist
										} else {
											frappe.msgprint(__('No bank entry found. ACH process cannot proceed.'));
										}
									}
								});
							}).addClass("btn-primary");
						}
					}
				}
			});
		}
	},

	add_print_checks_buttons: function (frm) {
		if (frm.doc.salary_slips_created && frm.doc.status !== "Queued") {
			frappe.call({
				method: 'us_payroll.custom_script.payroll_entry.get_submitted_check_stubs',
				args: {
					'doc_id': frm.doc.name
				},
				async: false, 
				callback: function(r) {
					var submitted_entries = r.message.submitted_entries;
					if (submitted_entries.length == 0) {
						frm.remove_custom_button("Print Checks");  
						frm.remove_custom_button("Print Void Check");          
					} else {

						if (!frm.custom_buttons["Print Checks"]) {
							frm.add_custom_button(__("Print Checks"), function () {
								console.log("check printed")
								frm.trigger('print_checks')
							}).addClass("btn-primary");
						}

						if (!frm.custom_buttons["Print Void Check"]) {
							frm.add_custom_button(__("Print Void Check"), function () {
								console.log("Print Void Check")
								frm.trigger('print_voids_checks')
							}).addClass("btn-primary");
						}
					}
				}
			});
		} 
	},

	print_checks:function(frm) {    
		frappe.call({
			method: 'us_payroll.custom_script.payroll_entry.get_salary_to_print',
			args: {
				'doc_id': frm.doc.name
			},
			callback: function(r) {
				var jvList = r.message;
				if (r.message && r.message.length > 0) {
					var letterhead = "No Letterhead"
					var pdf_options=  JSON.stringify({"page-size":"A4"});
					var json_string=JSON.stringify(jvList) 
		
					const w = window.open(
						"/api/method/frappe.utils.print_format.download_multi_pdf?" +
							"doctype=" +
							encodeURIComponent("Salary Slip") +
							"&name=" +
							encodeURIComponent(json_string) +
							"&format=" +
							encodeURIComponent("Check Stubs") +
							"&no_letterhead=1" +
							
							"&letterhead=" +
							encodeURIComponent(letterhead) +
							"&options=" +
							encodeURIComponent(pdf_options)
					);
		
					if (!w) {
						frappe.msgprint(__("Please enable pop-ups"));
						return;
					}

				} else {
					frappe.msgprint(__("No checks available")); 
				}	
			}
		});
	},

	redirection: function (frm) {
		let siteName = window.location.origin; 
		let dynamicPath = `/app/ach-report?payroll_entry=${frm.doc.name}`;
		window.open(siteName + dynamicPath, "_blank");
		
	},

	print_voids_checks:function(frm) {    
		frappe.call({
			method: 'us_payroll.custom_script.payroll_entry.get_salary_to_print_for_bank',
			args: {
				'doc_id': frm.doc.name
			},
			callback: function(r) {
				var jvList = r.message;
				if (r.message && r.message.length > 0) {
					var letterhead = "No Letterhead"
					var pdf_options=  JSON.stringify({"page-size":"A4"});
					var json_string=JSON.stringify(jvList) 
		
					const w = window.open(
						"/api/method/frappe.utils.print_format.download_multi_pdf?" +
							"doctype=" +
							encodeURIComponent("Salary Slip") +
							"&name=" +
							encodeURIComponent(json_string) +
							"&format=" +
							encodeURIComponent("Void Check Stubs") +
							"&no_letterhead=1" +
							
							"&letterhead=" +
							encodeURIComponent(letterhead) +
							"&options=" +
							encodeURIComponent(pdf_options)
					);
		
					if (!w) {
						frappe.msgprint(__("Please enable pop-ups"));
						return;
					}

				} else {
					frappe.msgprint(__("No void checks available")); 
				}	
			}
		});
	},

	make_dashboard:function(frm){
		$("div").remove(".form-dashboard-section.custom");
		if(frm.doc.start_date && frm.doc.end_date){
			frappe.call({
				method: 'us_payroll.custom_script.payroll_entry.render_html_for_holiday',
				args: {
					"start_date": frm.doc.start_date,
					"end_date": frm.doc.end_date
				},
				callback: function(r) {
					if (r.message && r.message.holidays) {                        
						let leave_details = r.message.holidays;
						
						// Remove existing section before adding a new one
						$("div").remove(".form-dashboard-section.custom");

						let holiday_html = `
							<div class="holiday-list">
								<h4>Holidays Between ${frm.doc.start_date} and ${frm.doc.end_date}</h4>
								<table class="table table-bordered">
									<thead>
										<tr>
											<th style="width: 50%;">Date</th>
											<th style="width: 50%;">Description</th>
										</tr>
									</thead>
									<tbody>
						`;

						leave_details.forEach(holiday => {
							holiday_html += `
								<tr>
									<td>${holiday.holiday_date}</td>
									<td>${holiday.description}</td>
								</tr>
							`;
						});

						holiday_html += `
									</tbody>
								</table>
							</div>
						`;

						frm.dashboard.add_section(holiday_html, __("Holidays"));
						frm.dashboard.show();
					} else {
						console.log("No Holidays Found.");
					}
				}
			});
		}
	},

	void_check: function (frm) { 
		if (frm.doc.docstatus == 1) {
			frappe.call({
				method: 'us_payroll.custom_script.payroll_entry.get_check_stubs_for_void_condition',
				args: {
					filters:{
						"payroll_entry": frm.doc.name,
						"docstatus": ["in", [0, 1]], 
						"custom_check_no": ["!=", ""]
					}
				},
				freeze:true,
				callback: function(r) {                             
					if(r.message.length > 0){   
						if (!frm.custom_buttons["Void Check"]) {
							frm.add_custom_button("Void Check", function() {
								voidCheck(frm);
							}).addClass("btn-primary");
						}
					}
				}
			})
		}   
	},
});

function voidCheck(frm) {     
	var d = new frappe.ui.Dialog({
			title: __('Check Number Details'),
			fields: [

				{
					label: "Select Check Number",
					fieldname: "salary_slip",
					fieldtype: "Link",
					options: "Salary Slip",
					get_query: function () {
						return {
							query: "us_payroll.custom_script.payroll_entry.get_check_to_void",
							filters: {
								payroll_entry: frm.doc.name
							}
						};
					}
				},
				{
					"label": "New check required?",
					"fieldname": "new_check_required",
					"fieldtype": "Check",
					"reqd": 1,
					"default": 1
				},
				{
					"label": "Reason",
					"fieldname": "reason",
					"fieldtype": "Data",
					"reqd": 1
				}

			],

			primary_action_label: 'Submit',
			primary_action(values) {            
					frappe.call({
							method: 'us_payroll.custom_script.payroll_entry.assign_new_check_no',
							args: {
								'source_name': values.salary_slip,
								'payroll_entry':frm.doc.name,
								'new_check_required': values.new_check_required,
								'reason': values.reason
							},
							freeze:true,
							callback: function(r) {
								d.hide()
								if (r.message && r.message.updated_slip){
									// window.location.reload();
									frappe.msgprint(`New check no <b>${r.message.new_check_no}</b> assigned to the employee <b>${r.message.emp_name}</b>`)
								}

								if (r.message && r.message.check_voided){
									frappe.msgprint("Check Voided/Cancelled")
								}
							}
						})
					
				}
			});

		d.show();
}


function calculate_holiday_hours(frm) {
	let total_holiday_hours = 0;
	if (!frm.doc.start_date || !frm.doc.end_date) {
		frappe.msgprint("Please select both Start Date and End Date.");
		return;
	}

	frappe.call({
		method: 'us_payroll.custom_script.payroll_entry.render_html_for_holiday',
		args: {
			"start_date": frm.doc.start_date,
			"end_date": frm.doc.end_date
		},
		callback: function(r) {
			if (r.message && r.message.holidays) {
				let leave_details = r.message.holidays;
				total_holiday_hours = leave_details.length * 8; // Each holiday = 8 hours

				if (frm.doc.employees && frm.doc.employees.length > 0) {
					frm.doc.employees.forEach(row => {
						row.custom_holiday_hours = total_holiday_hours;
						row.custom_holiday_amount = row.custom_hourly_rate * total_holiday_hours
					});
					frm.refresh_field("employees"); 
				}
			} else {
				console.log("No Holidays Found.");
				if (frm.doc.employees && frm.doc.employees.length > 0) {
					frm.doc.employees.forEach(row => {
						row.custom_holiday_hours = 0;
					});
					frm.refresh_field("employees"); 
				}
			}
		}
	});

	if (frm.doc.employees && frm.doc.employees.length > 0) {
		frm.doc.employees.forEach(row => {
			row.custom_holiday_amount = row.custom_hourly_rate * total_holiday_hours
		});
		frm.refresh_field("employees"); 
	}
}

let check_entry = function (frm) {
	var doc = frm.doc;
	if (doc.payment_account) {
		return frappe.call({
			method: "run_doc_method",
			args: {
				method: "make_check_entry",
				dt: "Payroll Entry",
				dn: frm.doc.name
			},
			callback: function () {
				frappe.set_route(
					'List', 'Journal Entry', {
						"Journal Entry Account.reference_name": frm.doc.name
					}
				);
			},
			freeze: true,
			freeze_message: __("Creating Payment Entries......")
		});
	} else {
		frappe.msgprint(__("Payment Account is mandatory"));
		frm.scroll_to_field('payment_account');
	}
};

const submit_salary_slip_no_freeze = function (frm) {
	frappe.confirm(
		__("This will submit Salary Slips and create accrual Journal Entry. Do you want to proceed?"),
		function () {
			frappe.call({
				method: "submit_salary_slips",
				doc: frm.doc,
				args: {},
				freeze: false,
			});
			frappe.show_alert({
				message: __("Salary Slips submission started in background."),
				indicator: "blue",
			});
		}
	);
};


frappe.ui.form.on('Payroll Employee Detail', {

	custom_comp_time: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.custom_comp_time && row.custom_hourly_rate) {
			row.custom_total_comp_time_amount = row.custom_comp_time * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}

		if (row.custom_comp_time == 0) {
			row.custom_total_comp_time_amount = row.custom_comp_time * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}
	},

	custom_pto_hours: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn]; 
		if (row.custom_pto_hours && row.custom_hourly_rate) {
			row.custom_pto_amount = row.custom_pto_hours * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}

		if (row.custom_pto_hours == 0) {
			row.custom_pto_amount = row.custom_pto_hours * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}

		if (row.custom_available_pto) {
	        let remaining_pto_hrs = 0
	        remaining_pto_hrs = row.custom_available_pto - row.custom_pto_hours
	        frappe.model.set_value(cdt, cdn, 'custom_available_pto', remaining_pto_hrs);
	    }    
	},

	custom_hourly_rate: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn]; 
		if (row.custom_comp_time && row.custom_hourly_rate) {
			row.custom_total_comp_time_amount = row.custom_comp_time * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}
	},

	employee:function(frm){
		// calculate_holiday_hours(frm)
	},

	custom_holiday_hours:function(frm, cdt, cdn){
		let row = locals[cdt][cdn]; 
		if (row.custom_holiday_hours && row.custom_hourly_rate) {
			console.log(row.custom_holiday_hours,"row.custom_holiday_hours",row.custom_hourly_rate,"row.custom_hourly_rate")
			row.custom_holiday_amount = row.custom_holiday_hours * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}
	},

	custom_hourly_rate:function(frm, cdt, cdn){
		let row = locals[cdt][cdn]; 
		if (row.custom_holiday_hours && row.custom_hourly_rate) {
			console.log(row.custom_holiday_hours,"row.custom_holiday_hours",row.custom_hourly_rate,"row.custom_hourly_rate")
			row.custom_holiday_amount = row.custom_holiday_hours * row.custom_hourly_rate;
			frm.refresh_field("employees"); 
		}
	},  

	custom_total_working_hours: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.employee) {
			frappe.msgprint(__('Please select an employee.'));
			return;
		}
		frappe.call({
			method: "us_payroll.custom_script.payroll_entry.get_department_working_hours",
			args: { employee: row.employee },
			callback: function(response) {
				if (response.message) {
					if (response.message.error) {
						frappe.msgprint(__(response.message.error));
						return;
					}

					frappe.db.get_single_value('Client Setup', 'default_working_hours')
					.then(default_hours => {

						let max_working_hours = response.message.working_hours;

						if (!max_working_hours || max_working_hours === 0) {
							max_working_hours = default_hours;
						}

						if (row.custom_total_working_hours > max_working_hours && max_working_hours > 0) {
							row.custom_total_overtime_hours = row.custom_total_working_hours - max_working_hours;
							row.custom_total_working_hours = max_working_hours;
						} else {
							row.custom_total_overtime_hours = 0;
						}

						frm.refresh_field('employees');
					});
				}
			}
		});
	}

});