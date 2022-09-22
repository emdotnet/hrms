# Copyright (c) 2022, Dokos SAS and Contributors
# License: See license.txt

import math
from datetime import timedelta
from typing import Optional

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, formatdate, getdate, nowdate, month_diff, get_last_day

from hrms.hr.utils import (
	get_earned_leaves,
	get_leave_allocations,
	create_additional_leave_ledger_entry,
	get_holidays_for_employee,
)

BDAY_MAP = {
	"monday": 0,
	"tuesday": 1,
	"wednesday": 2,
	"thursday": 3,
	"friday": 4,
	"saturday": 5,
	"sunday": 6,
}

def allocate_earned_leaves(date=None):
	EarnedLeaveAllocator(date).allocate()

class EarnedLeaveAllocator:
	def __init__(self, date=None):
		self.e_leave_types = get_earned_leaves()
		self.today = getdate(date or nowdate())

	def allocate(self):
		for e_leave_type in self.e_leave_types:
			leave_allocations = get_leave_allocations(self.today, e_leave_type.name)
			for allocation in leave_allocations:
				EarnedLeaveCalculator(self, e_leave_type, allocation).calculate_allocation()


class EarnedLeaveCalculator:
	def __init__(self, parent, leave_type, allocation):
		self.parent = parent
		self.leave_type = leave_type
		self.allocation = allocation
		self.period_start = self.allocation.from_date
		self.period_end = min(self.parent.today, self.allocation.to_date)
		self.annual_allocation = []
		self.attendance = {}
		self.earneable_leaves = 0
		self.earned_leaves = 0

		self.divide_by_frequency = {"Yearly": 1, "Half-Yearly": 6, "Quarterly": 4, "Monthly": 12}

	def calculate_allocation(self):
		if self.allocation.leave_policy_assignment and self.allocation.leave_policy:
			leave_policy = (
				self.allocation.leave_policy
				if self.allocation.leave_policy
				else frappe.db.get_value(
					"Leave Policy Assignment", self.allocation.leave_policy_assignment, ["leave_policy"]
				)
			)

			self.annual_allocation = frappe.db.get_value(
				"Leave Policy Detail",
				filters={"parent": leave_policy, "leave_type": self.leave_type.name},
				fieldname=["annual_allocation"],
			)
		else:
			self.annual_allocation = self.leave_type.max_leaves_allowed

		if self.annual_allocation:
			self.earneable_leaves = flt(self.annual_allocation) / 12
			self.get_attendance()

			if self.leave_type.earned_leave_frequency == "Congés payés sur jours ouvrables":
				self.conges_payes_ouvrables()

			elif self.leave_type.earned_leave_frequency == "Congés payés sur jours ouvrés":
				self.conges_payes_ouvres()

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
		# TODO: merge with allocate_earned_leaves_based_on_formula
		allocation = frappe.get_doc("Leave Allocation", self.allocation.name)
		new_allocation = flt(allocation.new_leaves_allocated) + flt(self.earned_leaves)

		if (
			new_allocation > self.leave_type.max_leaves_allowed and self.leave_type.max_leaves_allowed > 0
		):
			new_allocation = self.leave_type.max_leaves_allowed

		if new_allocation == allocation.total_leaves_allocated:
			return

		allocation_difference = flt(new_allocation) - flt(allocation.total_leaves_allocated)

		allocation.db_set("total_leaves_allocated", flt(new_allocation, 2), update_modified=False)
		create_additional_leave_ledger_entry(allocation, allocation_difference, self.parent.today)

		text = _("allocated {0} leave(s) via scheduler on {1}").format(
			frappe.bold(self.earned_leaves), frappe.bold(formatdate(self.parent.today))
		)

		allocation.add_comment(comment_type="Info", text=text)

	def conges_payes_ouvrables(self):
		months = month_diff(self.period_end, self.period_start)
		self.earned_leaves = min(
			self.earneable_leaves * flt(
				max(len(self.attendance.get("dates", [])) / 24, self.attendance.get("weeks", 0) / 4)
			),
			months * self.earneable_leaves
		)
		self.allocate_earned_leaves_based_on_formula()

	def conges_payes_ouvres(self):
		months = month_diff(self.period_end, self.period_start)
		self.earned_leaves = min(
			self.earneable_leaves * flt(
				max(len(self.attendance.get("dates", [])) / 20, self.attendance.get("weeks", 0) / 4)
			),
			months * self.earneable_leaves
		)

		if self.parent.today == get_last_day(self.parent.today) and self.earned_leaves < months * self.earneable_leaves and not self.attendance.get("leaves", []):
			self.earned_leaves = months * self.earneable_leaves

		self.allocate_earned_leaves_based_on_formula()

	def allocate_earned_leaves_based_on_formula(self):
		allocation = frappe.get_doc("Leave Allocation", self.allocation.name)
		new_allocation = flt(allocation.new_leaves_allocated) + flt(self.earned_leaves, precision=2)

		if (
			new_allocation > self.leave_type.max_leaves_allowed and self.leave_type.max_leaves_allowed > 0
		):
			new_allocation = self.leave_type.max_leaves_allowed

		if new_allocation == allocation.total_leaves_allocated:
			return

		if getdate(self.parent.today) >= getdate(allocation.to_date):
			new_allocation = math.ceil(flt(new_allocation))

		allocation_difference = flt(new_allocation) - flt(allocation.total_leaves_allocated) + flt(allocation.unused_leaves)

		allocation.db_set("total_leaves_allocated", flt(new_allocation, 2) + flt(allocation.unused_leaves, 2), update_modified=False)

		create_additional_leave_ledger_entry(allocation, allocation_difference, self.parent.today)


		text = _("allocated {0} leave(s) via scheduler on {1}").format(
			frappe.bold(self.earned_leaves), frappe.bold(formatdate(self.parent.today))
		)

		allocation.add_comment(comment_type="Info", text=text)

	def get_attendance(self):
		self.excluded_leave_types = [
			x.name for x in frappe.get_all("Leave Type", filters={"exclude_from_leave_acquisition": 1})
		]

		attendance = frappe.get_all(
			"Attendance",
			filters={
				"docstatus": 1,
				"employee": self.allocation.employee,
				"attendance_date": ("between", [self.period_start, self.period_end])
			},
			fields=["name", "attendance_date", "status", "leave_type"],
		)

		if frappe.db.get_single_value("HR Settings", "calculate_attendances"):
			return self.calculate_attendance(attendance)

		registered_attendance = [
			x for x in attendance if not (
				(x.status == "On Leave" and x.leave_type in self.excluded_leave_types)
				or x.status == "Absent"
			)
		]

		leaves = [
			x for x in attendance if (
				(x.status == "On Leave" and x.leave_type in self.excluded_leave_types)
				or x.status == "Absent"
			)
		]

		self.attendance = {
			"dates": registered_attendance,
			"weeks": len([x.attendance_date for x in registered_attendance]) / 7,
			"leaves": leaves
		}

	def calculate_attendance(self, attendance):
		employee_doc = frappe.db.get_value("Employee", self.allocation.employee, ["date_of_joining", "relieving_date"], as_dict=True)
		start_date = self.period_start
		end_date = min(self.parent.today, self.allocation.to_date)
		if employee_doc.date_of_joining:
			start_date = max(start_date, employee_doc.date_of_joining)
		if employee_doc.relieving_date:
			end_date = min(end_date, employee_doc.relieving_date)

		attendance_dates = [x.attendance_date for x in attendance if not (
				(x.status == "On Leave" and x.leave_type in self.excluded_leave_types)
				or x.status == "Absent"
			)
		]

		contracts_working_days = [
			BDAY_MAP.get(key) for x in
			frappe.get_all("Employment Contract",
				filters={
					"employee": self.allocation.employee,
					"company": self.allocation.company,
					"date_of_joining": ("<=", start_date),
					"ifnull(relieving_date, '2999-12-31')": (">=", end_date),
				},
				fields=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]) for key, value in x.items() if value
		]
		if contracts_working_days:
			attendance_dates = [x for x in attendance_dates if x.weekday() in contracts_working_days]

		absence_dates = [x.attendance_date for x in attendance if (
				(x.status == "On Leave" and x.leave_type in self.excluded_leave_types)
				or x.status == "Absent"
			)
		]

		if self.leave_type.earned_leave_frequency == "Congés payés sur jours ouvrables":
			holidays = [d.holiday_date for d in get_holidays_for_employee(self.allocation.employee, start_date, end_date) if not (d.weekly_off and d.holiday_date.weekday() == 5)]
		else:
			holidays = [d.holiday_date for d in get_holidays_for_employee(self.allocation.employee, start_date, end_date)]


		attendances = []

		for date in daterange(start_date, end_date):
			current_date = getdate(date)

			if current_date in attendance_dates:
				attendances.append(current_date)
			elif (current_date in holidays) or (current_date in absence_dates):
				continue
			else:
				attendances.append(current_date)

		self.attendance = {
			"dates": attendances,
			"weeks": len(attendances) / 7,
			"leaves": absence_dates
		}


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
		holidays = [d.holiday_date for d in get_holidays_for_employee(employee, from_date, add_days(to_date, -1)) if not (d.weekly_off and d.holiday_date.weekday() == 5)]
	else:
		holidays = [d.holiday_date for d in get_holidays_for_employee(employee, from_date, add_days(to_date, -1))]

	next_expected_working_day = add_days(getdate(from_date), 1)
	# If the first day is a saturday, it doesn't count as a leave
	if next_expected_working_day.weekday() == 5:
		next_expected_working_day = add_days(getdate(next_expected_working_day), 1)
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
	if not leave_type.include_holiday:
		number_of_days = flt(number_of_days) - flt(len([h for h in  holidays if getdate(h) > next_expected_working_day]))

	return number_of_days

def daterange(start_date, end_date):
	for n in range(int((end_date - start_date).days) + 1):
		yield start_date + timedelta(n)