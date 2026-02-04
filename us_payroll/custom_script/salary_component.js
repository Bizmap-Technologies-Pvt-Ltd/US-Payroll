
frappe.ui.form.on('Salary Component', {  
    
    custom_is_this_insurance_component: function(frm) {
        if (frm.doc.custom_is_this_insurance_component) {
            frm.set_value("custom_insurance_component", 1);
        } else {
            frm.set_value("custom_insurance_component", 0);
        }
        frm.refresh_field("custom_insurance_component");
    },

    custom_is_this_employers_insurance_component: function(frm) {
        if (frm.doc.custom_is_this_employers_insurance_component) {
            frm.set_value("custom_insurance_component", 1);
        } else {
            frm.set_value("custom_insurance_component", 0);
        }
        frm.refresh_field("custom_insurance_component");
    },


});


