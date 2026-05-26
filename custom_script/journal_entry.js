frappe.ui.form.on('Journal Entry', {
	
	setup: function(frm) {
		frm.trigger("replace_message");	
		frm.trigger("set_cheque_date");
	},

	validate:function(frm){
		frm.trigger("set_accounts_entries");
	},

	refresh:function(frm){
		frm.trigger('set_posting_date');
		frm.trigger('set_default_company');
		frm.trigger("set_cheque_date");	
	},

	onload:function(frm){
		frm.trigger('set_posting_date');
		frm.trigger('set_default_company');
		frm.trigger("set_cheque_date");
	},

	before_cancel: function(frm) {
        if (frm.doc.custom_batch_payment_entry || frm.doc.custom_receivable || frm.doc.custom_fund_expense || frm.doc.custom_journal_entry) {
            let msg = `Cannot cancel Journal Entry  <b> ${frm.doc.name} </b> because it is linked with the following references:<br>`;

            if (frm.doc.custom_batch_payment_entry) {
                msg += `<b><br>Batch Payment Entry:  ${frm.doc.custom_batch_payment_entry}</b>`;
            }
            if (frm.doc.custom_receivable) {
                msg += `<b><br>Receivable:  ${frm.doc.custom_receivable}</b>`;
            }
            if (frm.doc.custom_fund_expense) {
                msg += `<b><br>Fund Expense:  ${frm.doc.custom_fund_expense}</b>`;
            }
            if (frm.doc.custom_journal_entry) {
                msg += `<b><br>Journal Entry:  ${frm.doc.custom_journal_entry}</b>`;
            }

            frappe.msgprint({
                title: __('Cannot Cancel'),
                indicator: 'red',
                message: __(msg)
            });

            // Prevent the cancel operation
            frappe.validated = false;
        }
    },

    set_default_company:function(frm){
    	if (frm.doc.__islocal == 1) {
	        frappe.call({
	            method: 'us_payroll.custom_script.journal_entry.get_global_defaults_values',
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

    replace_message:function(frm){
		frappe.confirm = function (message, confirm_action, reject_action) {	
			message = message.replace("Permanently", "").trim();
			var d = new frappe.ui.Dialog({
				title: __("Confirm", null, "Title of confirmation dialog"),
				primary_action_label: __("Yes", null, "Approve confirmation dialog"),
				primary_action: () => {
					confirm_action && confirm_action();
					d.hide();
				},
				secondary_action_label: __("No", null, "Dismiss confirmation dialog"),
				secondary_action: () => d.hide(),
			});

			d.$body.append(`<p class="frappe-confirm-message">${message}</p>`);
			d.show();

			// flag, used to bind "okay" on enter
			d.confirm_dialog = true;

			// no if closed without primary action
			if (reject_action) {
				d.onhide = () => {
					if (!d.primary_action_fulfilled) {
						reject_action();
					}
				};
			}

			return d;
		};
	},

    set_posting_date:function(frm){
    	const today = frappe.datetime.get_today();
    	if (frm.doc.__islocal == 1) {   		
	    	frm.set_value('posting_date', today);
	    }
    },

    set_cheque_date:function(frm){
    	console.log("call======")
    	const today = frappe.datetime.get_today();
		frm.set_value('cheque_date', today);  
    },


	set_accounts_entries:function(frm){
		var debit = 0
		var credit = 0
		var total_debit = 0
		var total_credit = 0
		var fund_wise = {}

		$.each(frm.doc.accounts,function(idx,row){
			var fund_name = row.fund
			if (!fund_wise[fund_name]){
				fund_wise[fund_name]={'credit':0,'debit':0}
			}

			if (row.debit_in_account_currency){
				fund_wise[fund_name]["debit"] += row.debit_in_account_currency			
			}	

			if (row.credit_in_account_currency){
				fund_wise[fund_name]['credit'] += row.credit_in_account_currency		
			}			
		})

		$.each(fund_wise, function(key, value) {
			let credit = parseFloat(value['credit'].toFixed(2));
			let debit = parseFloat(value['debit'].toFixed(2));
		
			if (credit !== debit) {
				frappe.throw(`Total Debit must be equal to Total Credit for fund ${key}`);
				frappe.validated = false;
			}
		});		
	},

});