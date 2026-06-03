frappe.ui.form.on('Attendance', {
	refresh:function(frm){
		frm.trigger("set_default_company");
		frm.trigger("calculate_ot");
	},

	onload:function(frm){
		frm.trigger("set_default_company");
	},

	validate:function(frm){
		frm.trigger("set_default_company");
		frm.trigger("calculate_ot");
	},

	set_default_company:function(frm){
    	if (frm.doc.__islocal == 1) {
	        frappe.call({
	            method: 'us_payroll.custom_script.attendance.get_global_defaults_values',
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

    calculate_ot:function(frm){
		if (!frm.doc.employee) {
			frappe.msgprint(__('Please select an employee.'));
			return;
		}
		frappe.call({
			method: "us_payroll.custom_script.attendance.get_department_working_hours",
			args: { employee: frm.doc.employee },
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

						if (frm.doc.working_hours > max_working_hours && max_working_hours > 0) {
							frm.doc.custom_overtime_hours = frm.doc.working_hours - max_working_hours;
							frm.doc.working_hours = max_working_hours;
						} else {
							frm.doc.custom_overtime_hours = 0;
						}
						frm.refresh_field('working_hours');
						frm.refresh_field('custom_overtime_hours');
						
					});
				}
			}
		});
	},
});
