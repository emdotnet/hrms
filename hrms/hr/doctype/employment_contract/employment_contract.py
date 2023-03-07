# Copyright (c) 2021, Dokos SAS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint

from hrms.hr.utils import allocate_earned_leaves


class EmploymentContract(Document):
	def validate(self):
		self.weekly_working_hours = self.weekly_working_hours or sum(
			[
				flt(self.monday),
				flt(self.tuesday),
				flt(self.wednesday),
				flt(self.thursday),
				flt(self.friday),
				flt(self.saturday),
				flt(self.sunday),
			]
		)

	@frappe.whitelist()
	def update_leaves(self):
		if not cint(frappe.db.get_single_value("HR Settings", "allocate_leaves_from_contracts")):
			frappe.throw(_("Please allow leaves allocation from contracts in HR Settings"))

		allocate_earned_leaves(contract=self.name)