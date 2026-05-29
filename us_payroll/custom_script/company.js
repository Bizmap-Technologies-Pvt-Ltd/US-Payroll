frappe.ui.form.on('Company', {

    validate: function(frm) {
        frm.trigger("ein_no_validation");
    },

    ein_no_validation: function(frm) {
        let ein = frm.doc.tax_id;
        if (ein) {
            if (ein.length === 9) {
                frm.set_value('tax_id', ein);
            } else {
                frm.set_value('tax_id', "");
                frappe.msgprint(__('EIN No. should be 9 digits.'));
            }
        }
    },

});
