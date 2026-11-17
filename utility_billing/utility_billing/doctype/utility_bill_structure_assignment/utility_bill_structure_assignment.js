frappe.ui.form.on('Utility Bill Structure Assignment', {
    refresh(frm) {
        frm.set_query('utility_bill_structure', () => ({filters: {docstatus: 1, company: frm.doc.company}}));
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Change Bill Structure'), () => {
                frappe.prompt([
                    {fieldname: 'new_structure', fieldtype: 'Link', options: 'Utility Bill Structure', label: __('New Bill Structure'), reqd: 1,
                     get_query: () => ({filters: {docstatus: 1, company: frm.doc.company, name: ['!=', frm.doc.utility_bill_structure]}})},
                    {fieldname: 'effective_date', fieldtype: 'Date', label: __('Effective Date'), reqd: 1, default: frappe.datetime.get_today()}
                ], values => frm.call('change_structure', values).then(r => {
                    if (r.message) frappe.set_route('Form', 'Utility Bill Structure Assignment', r.message);
                }), __('Change Bill Structure'), __('Create Assignment'));
            });
            frm.add_custom_button(__('Create Monthly Bill'), () => {
                frappe.new_doc('Meter Reading', {
                    customer: frm.doc.customer,
                    company: frm.doc.company,
                    property: frm.doc.property,
                    bill_structure_assignment: frm.doc.name,
                    date: frappe.datetime.get_today()
                });
            });
        }
    }
});
