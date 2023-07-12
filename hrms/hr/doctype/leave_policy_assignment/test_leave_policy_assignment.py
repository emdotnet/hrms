# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_first_day, getdate

from hrms.hr.doctype.leave_application.test_leave_application import get_employee, get_leave_period
from hrms.hr.doctype.leave_policy.test_leave_policy import create_leave_policy
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	create_assignment_for_multiple_employees,
)

test_dependencies = ["Employee"]


class TestLeavePolicyAssignment(FrappeTestCase):
	def setUp(self):
		for doctype in [
			"Leave Period",
			"Leave Application",
			"Leave Allocation",
			"Leave Policy Assignment",
			"Leave Ledger Entry",
		]:
			frappe.db.delete(doctype)

		employee = get_employee()
		self.original_doj = employee.date_of_joining
		self.employee = employee

	def test_grant_leaves(self):
		leave_period = get_leave_period()
		leave_policy = create_leave_policy(annual_allocation=10)
		leave_policy.submit()

		self.employee.date_of_joining = get_first_day(leave_period.from_date)
		self.employee.save()

		data = frappe._dict(
			{
				"assignment_based_on": "Leave Period",
				"leave_policy": leave_policy.name,
				"leave_period": leave_period.name,
			}
		)
		assignments = create_assignment_for_multiple_employees([self.employee.name], data)
		self.assertEqual(
			frappe.db.get_value("Leave Policy Assignment", assignments[0], "leaves_allocated"),
			1,
		)

		allocation = frappe.db.get_value(
			"Leave Allocation", {"leave_policy_assignment": assignments[0]}, "name"
		)

		leave_alloc_doc = frappe.get_doc("Leave Allocation", allocation)

		self.assertEqual(leave_alloc_doc.new_leaves_allocated, 10)
		self.assertEqual(leave_alloc_doc.leave_type, "_Test Leave Type")
		self.assertEqual(getdate(leave_alloc_doc.from_date), getdate(leave_period.from_date))
		self.assertEqual(getdate(leave_alloc_doc.to_date), getdate(leave_period.to_date))
		self.assertEqual(leave_alloc_doc.leave_policy, leave_policy.name)
		self.assertEqual(leave_alloc_doc.leave_policy_assignment, assignments[0])

	def test_allow_to_grant_all_leave_after_cancellation_of_every_leave_allocation(self):
		leave_period = get_leave_period()
		# create the leave policy with leave type "_Test Leave Type", allocation = 10
		leave_policy = create_leave_policy()
		leave_policy.submit()

		leave_policy = create_leave_policy(annual_allocation=10)
		leave_policy.submit()

		data = frappe._dict(
			{
				"assignment_based_on": "Leave Period",
				"leave_policy": leave_policy.name,
				"leave_period": leave_period.name,
			}
		)
		assignments = create_assignment_for_multiple_employees([self.employee.name], data)

		# every leave is allocated no more leave can be granted now
		self.assertEqual(
			frappe.db.get_value("Leave Policy Assignment", assignments[0], "leaves_allocated"),
			1,
		)
		allocation = frappe.db.get_value(
			"Leave Allocation", {"leave_policy_assignment": assignments[0]}, "name"
		)

		leave_alloc_doc = frappe.get_doc("Leave Allocation", allocation)
		leave_alloc_doc.cancel()
		leave_alloc_doc.delete()
		self.assertEqual(
			frappe.db.get_value("Leave Policy Assignment", assignments[0], "leaves_allocated"),
			0,
		)

	def test_pro_rated_leave_allocation(self):
		leave_period = get_leave_period()
		leave_policy = create_leave_policy(annual_allocation=12)
		leave_policy.submit()

		self.employee.date_of_joining = add_months(leave_period.from_date, 3)
		self.employee.save()

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}
		assignments = create_assignment_for_multiple_employees([self.employee.name], frappe._dict(data))

		allocation = frappe.db.get_value(
			"Leave Allocation", {"leave_policy_assignment": assignments[0]}, "new_leaves_allocated"
		)

		# pro-rated leave allocation for 9 months
		self.assertEqual(allocation, 9)

	def tearDown(self):
		frappe.db.set_value("Employee", self.employee.name, "date_of_joining", self.original_doj)
		frappe.flags.current_date = None


def create_earned_leave_type(leave_type, based_on_doj=False):
	frappe.delete_doc_if_exists("Leave Type", leave_type, force=1)

	return frappe.get_doc(
		dict(
			leave_type_name=leave_type,
			doctype="Leave Type",
			is_earned_leave=1,
			earned_leave_frequency="Monthly",
			rounding=0.5,
			is_carry_forward=1,
			based_on_date_of_joining=based_on_doj,
		)
	).insert()


def create_leave_period(name, start_date=None):
	frappe.delete_doc_if_exists("Leave Period", name, force=1)
	if not start_date:
		start_date = get_first_day(getdate())

	return frappe.get_doc(
		dict(
			name=name,
			doctype="Leave Period",
			from_date=start_date,
			to_date=add_months(start_date, 12),
			company="_Test Company",
			is_active=1,
			leave_types=[{"leave_type": lt.name} for lt in frappe.get_all("Leave Type")],
		)
	).insert()


def setup_leave_period_and_policy(start_date, based_on_doj=False):
	leave_type = create_earned_leave_type("Test Earned Leave", based_on_doj)
	leave_period = create_leave_period("Test Earned Leave Period", start_date=start_date)
	leave_policy = frappe.get_doc(
		{
			"doctype": "Leave Policy",
			"title": "Test Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}],
		}
	).insert()

	return leave_period, leave_policy
