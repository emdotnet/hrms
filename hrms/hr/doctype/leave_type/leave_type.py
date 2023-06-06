# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from calendar import monthrange

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import today, getdate, cint, add_to_date

STANDARD_EARNED_LEAVES_FREQUENCIES = ["Monthly", "Quarterly", "Half-Yearly", "Yearly"]

class LeaveType(Document):
	def validate(self):
		self.validate_lwp()
		self.validate_leave_types()

	def validate_lwp(self):
		if self.is_lwp:
			leave_allocation = frappe.get_all(
				"Leave Allocation",
				filters={"leave_type": self.name, "from_date": ("<=", today()), "to_date": (">=", today())},
				fields=["name"],
			)
			leave_allocation = [l["name"] for l in leave_allocation]
			if leave_allocation:
				frappe.throw(
					_(
						"Leave application is linked with leave allocations {0}. Leave application cannot be set as leave without pay"
					).format(", ".join(leave_allocation))
				)  # nosec

	def validate_leave_types(self):
		if self.is_compensatory and self.is_earned_leave:
			msg = _("Leave Type can either be compensatory or earned leave.") + "<br><br>"
			msg += _("Earned Leaves are allocated as per the configured frequency via scheduler.") + "<br>"
			msg += _(
				"Whereas allocation for Compensatory Leaves is automatically created or updated on submission of Compensatory Leave Request."
			)
			msg += "<br><br>"
			msg += _("Disable {0} or {1} to proceed.").format(
				bold(_("Is Compensatory Leave")), bold(_("Is Earned Leave"))
			)
			frappe.throw(msg, title=_("Not Allowed"))

		if self.is_lwp and self.is_ppl:
			frappe.throw(_("Leave Type can either be without pay or partial pay"), title=_("Not Allowed"))

		if self.is_ppl and (
			self.fraction_of_daily_salary_per_leave < 0 or self.fraction_of_daily_salary_per_leave > 1
		):
			frappe.throw(_("The fraction of Daily Salary per Leave should be between 0 and 1"))

		self.validate_periods()

	def validate_periods(self):
		if frappe.flags.in_install or frappe.flags.in_migrate:
			return

		for field in ["period_start_month", "period_end_month"]:
			if 12 > cint(self.get(field)) < 1:
				frappe.throw(_("The month must be between 1 and 12"))

		for combination in [{"period_start_day": self.period_start_month}, {"period_end_day": self.period_end_month}]:
			for start_date, start_month in combination.items():
				start_month_range = monthrange(getdate().year, start_month)
				if start_month == 2:
					start_month_range = (2, 28)
				if cint(self.get(start_date)) < 1 or cint(self.get(start_date)) > start_month_range[1]:
					frappe.throw(_("The date must be between 1 and {0}").format(start_month_range[1]))

	def get_period_start_date(self, date=None):
		current_year_start = getdate(date).replace(month=self.period_start_month, day=self.period_start_day)
		if current_year_start > getdate(date):
			return getdate(add_to_date(current_year_start, years=-1))
		elif current_year_start == getdate(date):
			return getdate(date)

		return current_year_start

	def get_period_end_date(self, date=None):
		current_year_end = getdate(date).replace(month=self.period_end_month, day=self.period_end_day)
		if current_year_end < getdate(date):
			return getdate(add_to_date(current_year_end, years=1))
		elif current_year_end == getdate(date):
			return getdate(date)

		return current_year_end