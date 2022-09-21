frappe.ui.form.on('Leave Type', {
	refresh(frm) {
		frm.toggle_display("is_ppl", false);
	}
})