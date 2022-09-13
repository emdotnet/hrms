# Copyright (c) 2022, Dokos SAS and Contributors
# License: See license.txt

import math
from typing import Optional

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, formatdate, getdate, nowdate

from hrms.hr.utils import (
	get_earned_leaves,
	get_leave_allocations,
	create_additional_leave_ledger_entry,
	get_holidays_for_employee,
)


def allocate_earned_leaves():
	FranceLeaveAllocator(FranceLeaveCalculator).allocate()

class EarnedLeaveAllocator:
	def __init__(self, calculator, date=None):
		self.calculator = calculator
		self.e_leave_types = get_earned_leaves()
		self.today = getdate(date or nowdate())

	def allocate(self):
		for e_leave_type in self.e_leave_types:
			leave_allocations = get_leave_allocations(self.today, e_leave_type.name)

			for allocation in leave_allocations:
				self.calculator(self, e_leave_type, allocation).calculate_allocation()


class EarnedLeaveCalculator:
	def __init__(self, parent, leave_type, allocation):
		super(EarnedLeaveCalculator, self).__init__()
		self.parent = parent
		self.leave_type = leave_type
		self.allocation = allocation
		self.leave_policy = None
		self.annual_allocation = []
		self.attendance = {}
		self.earneable_leaves = 0
		self.earned_leaves = 0

		self.formula_map = {}
		self.divide_by_frequency = {"Yearly": 1, "Half-Yearly": 6, "Quarterly": 4, "Monthly": 12}

	def calculate_allocation(self):
		if not self.allocation.leave_policy_assignment and not self.allocation.leave_policy:
			return

		self.leave_policy = (
			self.allocation.leave_policy
			if self.allocation.leave_policy
			else frappe.db.get_value(
				"Leave Policy Assignment", self.allocation.leave_policy_assignment, ["leave_policy"]
			)
		)

		self.annual_allocation = frappe.db.get_value(
			"Leave Policy Detail",
			filters={"parent": self.leave_policy, "leave_type": self.leave_type.name},
			fieldname=["annual_allocation"],
		)

		if self.annual_allocation:
			self.earneable_leaves = flt(self.annual_allocation) / 12
			self.attendance = get_attendance(
				self.allocation.employee,
				self.allocation.from_date,
				min(self.parent.today, self.allocation.to_date),
			)

			if (
				self.leave_type.earned_leave_frequency in ("Congés payés sur jours ouvrables", "Congés payés sur jours ouvrés")
			):
				self.formula_map.get(self.leave_type.earned_leave_frequency)()

			elif self.leave_type.earned_leave_frequency in ("Monthly", "Quarterly", "Half-Yearly", "Yearly"):
				self.earned_leaves = (
					flt(self.annual_allocation) / self.divide_by_frequency[self.leave_type.earned_leave_frequency]
				)
				if self.leave_type.rounding == "None":
					pass
				elif self.leave_type.rounding == "0.5":
					self.earned_leaves = round(self.earned_leaves * 2) / 2
				else:
					self.earned_leaves = round(self.earned_leaves)

				self.allocate_earned_leaves()

	def allocate_earned_leaves(self):
		allocation = frappe.get_doc("Leave Allocation", self.allocation.name)
		new_allocation = flt(allocation.new_leaves_allocated) + flt(self.earned_leaves)

		if (
			new_allocation > self.leave_type.max_leaves_allowed and self.leave_type.max_leaves_allowed > 0
		):
			new_allocation = self.leave_type.max_leaves_allowed

		if new_allocation == allocation.total_leaves_allocated:
			return

		allocation_difference = flt(new_allocation) - flt(allocation.total_leaves_allocated)

		allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
		create_additional_leave_ledger_entry(allocation, allocation_difference, self.parent.today)

		text = _("allocated {0} leave(s) via scheduler on {1}").format(
			frappe.bold(self.earned_leaves), frappe.bold(formatdate(self.parent.today))
		)

		allocation.add_comment(comment_type="Info", text=text)


class FranceLeaveAllocator(EarnedLeaveAllocator):
	def __init__(self, calculator, date=None):
		super(FranceLeaveAllocator, self).__init__(calculator, date)


class FranceLeaveCalculator(EarnedLeaveCalculator):
	def __init__(self, parent, leave_type, allocation):
		super(FranceLeaveCalculator, self).__init__(parent, leave_type, allocation)
		self.formula_map = {
			"Congés payés sur jours ouvrables": self.conges_payes_ouvrables,
			"Congés payés sur jours ouvrés": self.conges_payes_ouvres,
		}

	def conges_payes_ouvrables(self):
		self.earned_leaves = self.earneable_leaves * flt(
			max(
				round(len(self.attendance.get("dates", [])) / 24), round(self.attendance.get("weeks", 0) / 4)
			)
		)
		self.allocate_earned_leaves_based_on_formula()

	def conges_payes_ouvres(self):
		self.earned_leaves = self.earneable_leaves * flt(
			max(
				round(len(self.attendance.get("dates", [])) / 20), round(self.attendance.get("weeks", 0) / 4)
			)
		)
		self.allocate_earned_leaves_based_on_formula()

	def allocate_earned_leaves_based_on_formula(self):
		allocation = frappe.get_doc("Leave Allocation", self.allocation.name)
		new_allocation = flt(allocation.new_leaves_allocated) + flt(self.earned_leaves)

		if (
			new_allocation > self.leave_type.max_leaves_allowed and self.leave_type.max_leaves_allowed > 0
		):
			new_allocation = self.leave_type.max_leaves_allowed

		if new_allocation == allocation.total_leaves_allocated:
			return

		if getdate(self.parent.today) >= getdate(
			frappe.db.get_value("Leave Period", allocation.leave_period, "to_date")
		):
			new_allocation = math.ceil(flt(new_allocation))

		allocation_difference = flt(new_allocation) - flt(allocation.total_leaves_allocated)

		allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
		create_additional_leave_ledger_entry(allocation, allocation_difference, self.parent.today)

		text = _("allocated {0} leave(s) via scheduler on {1}").format(
			frappe.bold(self.earned_leaves), frappe.bold(formatdate(self.parent.today))
		)

		allocation.add_comment(comment_type="Info", text=text)


def get_regional_number_of_leave_days(
	employee: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	half_day: Optional[int] = None,
	half_day_date: Optional[str] = None,
	holiday_list: Optional[str] = None,
) -> float:
	"""Returns number of leave days between 2 dates after considering half day and holidays
	(Based on the include_holiday setting in Leave Type)"""
	holidays = [d.holiday_date for d in get_holidays_for_employee(employee, from_date, to_date)]
	next_expected_working_day = add_days(getdate(from_date), 1)
	while next_expected_working_day in holidays:
		next_expected_working_day = add_days(getdate(next_expected_working_day), 1)

	number_of_days = 0
	if cint(half_day) == 1:
		if getdate(from_date) == getdate(to_date):
			number_of_days = 0.5
		elif half_day_date and getdate(next_expected_working_day) <= getdate(half_day_date) <= getdate(
			to_date
		):
			number_of_days = date_diff(to_date, next_expected_working_day) + 0.5
		else:
			number_of_days = date_diff(to_date, next_expected_working_day)
	else:
		number_of_days = date_diff(to_date, next_expected_working_day)

	leave_type = frappe.db.get_value(
		"Leave Type",
		leave_type,
		[
			"include_holiday",
			"is_earned_leave",
			"earned_leave_frequency",
		],
		as_dict=True,
	)

	if leave_type.is_earned_leave and leave_type.earned_leave_frequency == "Congés payés sur jours ouvrables":
		# TODO: Appliquer la règle des 5 samedis maximum
		non_weekly_holidays = [
			d.holiday_date
			for d in get_holidays_for_employee(employee, from_date, to_date, only_non_weekly=True)
		]
		holidays = [d for d in holidays if d.day != 6 and d not in non_weekly_holidays]

	if not leave_type.include_holiday:
		number_of_days = flt(number_of_days) - flt(holidays)

	return number_of_days

def get_attendance(employee, start_date, end_date):
	excluded_leave_types = [
		x.name for x in frappe.get_all("Leave Type", filters={"exclude_from_leave_acquisition": 1})
	]

	attendance = frappe.get_all(
		"Attendance",
		filters={
			"docstatus": 1,
			"employee": employee,
			"attendance_date": ("between", [start_date, end_date]),
			"status": ("!=", "Absent"),
		},
		fields=["name", "attendance_date", "status", "leave_type"],
	)
	attendance = [
		x for x in attendance if not (x.status == "On Leave" and x.leave_type in excluded_leave_types)
	]

	return {
		"dates": attendance,
		"weeks": len([x.attendance_date for x in attendance]) / 7,
	}