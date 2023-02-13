# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from calendar import monthrange

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate, cint, add_to_date

STANDARD_EARNED_LEAVES_FREQUENCIES = ["Monthly", "Quarterly", "Half-Yearly", "Yearly"]

class LeaveType(Document):
	def validate(self):
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

		if self.is_lwp and self.is_ppl:
			frappe.throw(_("Leave Type can be either without pay or partial pay"))

		if self.is_ppl and (
			self.fraction_of_daily_salary_per_leave < 0 or self.fraction_of_daily_salary_per_leave > 1
		):
			frappe.throw(_("The fraction of Daily Salary per Leave should be between 0 and 1"))

		self.validate_periods()

	def validate_periods(self):
		for field in ["period_start_month", "period_end_month"]:
			if 12 > cint(self.get(field)) < 1:
				frappe.throw(_("The month must be between 1 and 12"))

		for combination in [{"period_start_day": self.period_start_month}, {"period_end_day": self.period_start_month}]:
			for start_date, start_month in combination.items():
				start_month_range = monthrange(getdate().year, start_month)
				if start_month == 2:
					start_month_range = (2, 28)
				if cint(self.get(start_date)) < 1 or cint(self.get(start_date)) > start_month_range[1]:
					frappe.throw(_("The date must be between 1 and {0}").format(start_month_range[1]))

	def get_period_start_date(self):
		current_year_start = getdate().replace(month=self.period_start_month, day=self.period_start_day)
		if current_year_start >= getdate():
			return getdate(add_to_date(current_year_start, years=-1))

		return current_year_start

	def get_period_end_date(self):
		current_year_end = getdate().replace(month=self.period_end_month, day=self.period_end_day)
		if current_year_end <= getdate():
			return getdate(add_to_date(current_year_end, years=1))

		return current_year_end