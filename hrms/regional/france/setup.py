# Copyright (c) 2022, Dokos SAS and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _, make_property_setter
from frappe.permissions import setup_custom_perms
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup(company=None, patch=True):
	make_property_setters()
	make_custom_fields()
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
		},
		{
			"doctype": "HR Settings",
			"fieldname": "auto_leave_encashment",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
		}
	]
	for property_setter in property_setters:
		make_property_setter(
			property_setter,
			is_system_generated=True,
		)

def make_custom_fields(update=True):
	# Keep for translations: _("Calculate attendances") _(""Allocate Leaves from Contracts"")
	# _("Attendances for each employee will be calculated and don't need to be explicitely registered")
	# _("Leave allocations will automatically attributed based on the rule defined in the employment contract")
	custom_fields = {
		"HR Settings": [
			dict(
				fieldname="calculate_attendances",
				label="Calculate attendances",
				description="Attendances for each employee will be calculated and don't need to be explicitely registered",
				fieldtype="Check",
				insert_after="auto_leave_encashment"
			),
			dict(
				fieldname="allocate_leaves_from_contracts",
				label="Allocate Leaves from Contracts",
				description="Leave allocations will automatically attributed based on the rule defined in the employment contract",
				fieldtype="Check",
				insert_after="calculate_attendances"
			)
		],
	}

	create_custom_fields(custom_fields, ignore_validate=frappe.flags.in_patch, update=update)

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
			"max_leaves_allowed": 8,
			"period_start_day": 1,
			"period_start_month": 1,
			"period_end_day": 31,
			"period_end_month": 12
		},
		{
			"doctype": "Leave Type",
			"leave_type_name": _("Congés Payés"),
			"name": _("Congés Payés"),
			"allow_encashment": 0,
			"is_carry_forward": 1,
			"include_holiday": 0,
			"is_compensatory": 0,
			"max_leaves_allowed": 30,
			"allow_negative": 1,
			"is_earned_leave": 1,
			"earned_leave_frequency": "Congés payés sur jours ouvrables",
			"period_start_day": 1,
			"period_start_month": 6,
			"period_end_day": 31,
			"period_end_month": 5
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
			"period_start_day": 1,
			"period_start_month": 1,
			"period_end_day": 31,
			"period_end_month": 12
		},
	]

	for leave_type in leave_types:
		if frappe.db.exists("Leave Type", leave_type.get("leave_type_name")):
			doc = frappe.get_doc("Leave Type", leave_type.get("leave_type_name"))
			doc.update(leave_type)
			doc.flags.ignore_permissions = True
			doc.save()
		else:
			doc = frappe.get_doc(leave_type)
			doc.insert(ignore_permissions=True, ignore_if_duplicate=True)


def setup_document_permissions():
	setup_custom_perms("Leave Encashment")

	ptypes = [field.fieldname for field in frappe.get_meta("Custom DocPerm").fields if field.fieldtype == "Check"]
	for permdoc in frappe.get_all("Custom DocPerm", filters={"parent": "Leave Encashment"}):
		doc = frappe.get_doc("Custom DocPerm", permdoc.name)
		for ptype in ptypes:
			doc.set(ptype, 0)

		doc.save()