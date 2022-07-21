# Copyright (c) 2022, Dokos SAS and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _


def setup(company=None, patch=True):
	setup_default_leaves()

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
			"earned_leave_frequency": "Custom Formula",
			"earned_leave_frequency_formula": "Congés payés sur jours ouvrables",
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
