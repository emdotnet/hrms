# Copyright (c) 2022, Dokos SAS and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _, make_property_setter
from frappe.permissions import setup_custom_perms

def setup(company=None, patch=True):
	make_property_setters()
	setup_default_leaves()
	setup_document_permissions()

def make_property_setters():
	property_setters = [
		{
			"doctype": "Leave Type",
			"fieldname": "earned_leave_frequency",
			"property": "options",
			"value": "Monthly\nQuarterly\nHalf-Yearly\nYearly\nCongés payés sur jours ouvrables\nCongés payés sur jours ouvrés",
			"property_type": "Select",
		},
		{
			"doctype": "Leave Type",
			"fieldname": "encashment",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
		},
		{
			"doctype": "Leave Type",
			"fieldname": "based_on_date_of_joining",
			"property": "depends_on",
			"value": "eval:doc.is_earned_leave&&['Monthly', 'Quarterly', 'Half-Yearly', 'Yearly'].includes(doc.earned_leave_frequency)",
			"property_type": "Code",
		},
		{
			"doctype": "Leave Type",
			"fieldname": "rounding",
			"property": "depends_on",
			"value": "eval:doc.is_earned_leave&&['Monthly', 'Quarterly', 'Half-Yearly', 'Yearly'].includes(doc.earned_leave_frequency)",
			"property_type": "Code",
		}
	]
	for property_setter in property_setters:
		make_property_setter(
			property_setter,
			is_system_generated=True,
		)

def setup_default_leaves():
	leave_types = [
		{
			"doctype": "Leave Type",
			"leave_type_name": _("RTT"),
			"name": _("RTT"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 0,
			"is_compensatory": 0,
			"max_leaves_allowed": 0,
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Congés Payés"),
			"name": _("Congés Payés"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 0,
			"is_compensatory": 0,
			"max_leaves_allowed": 30,
			"allow_negative": 1,
			"is_earned_leave": 1,
			"earned_leave_frequency": "Congés payés sur jours ouvrables",
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Sick Leave"),
			"name": _("Sick Leave"),
			"allow_encashment": 0,
			"is_carry_forward": 0,
			"include_holiday": 0,
			"is_compensatory": 0,
			"max_leaves_allowed": 0,
			"allow_negative": 1,
			"is_lwp": 1,
		},
	]

	for leave_type in leave_types:
		doc = frappe.get_doc(leave_type)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)

	policy = {
		"doctype": "Leave Policy",
		"title": _("Congés Payés"),
		"leave_policy_details": [{"leave_type": _("Congés Payés"), "annual_allocation": 30}],
	}

	doc = frappe.get_doc(policy)
	doc.insert(ignore_permissions=True, ignore_if_duplicate=True)

def setup_document_permissions():
	setup_custom_perms("Leave Encashment")

	ptypes = [field.fieldname for field in frappe.get_meta("Custom DocPerm").fields if field.fieldtype == "Check"]
	for permdoc in frappe.get_all("Custom DocPerm", filters={"parent": "Leave Encashment"}):
		doc = frappe.get_doc("Custom DocPerm", permdoc.name)
		for ptype in ptypes:
			doc.set(ptype, 0)

		doc.save()