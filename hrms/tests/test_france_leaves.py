import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, get_last_day, month_diff, flt

from erpnext.setup.doctype.employee.test_employee import make_employee

from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list
from hrms.regional.france.hr.bank_holidays import get_french_bank_holidays
from hrms.regional.france.setup import setup
from hrms.regional.france.hr.utils import daterange, allocate_earned_leaves
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import process_expired_allocation

PERIODS = [
	("2018-06-01", "2019-05-31"),
	("2019-06-01", "2020-05-31"),
	("2020-06-01", "2021-05-31"),
	("2021-06-01", "2022-05-31"),
	("2022-06-01", "2023-05-31")
]


class TestFranceLeavesCalculation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		frappe.flags.country = "France"

		setup()

		frappe.db.set_single_value("HR Settings", "allocate_leaves_from_contracts", 1)
		frappe.db.set_single_value("HR Settings", "calculate_attendances", 1)

		leave_types = [
			{
				"doctype": "Leave Type",
				"leave_type_name": "Congés Payés sur jours ouvrables",
				"name": "Congés Payés sur jours ouvrables",
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
				"leave_type_name": "Congés Payés sur jours ouvrés",
				"name": "Congés Payés sur jours ouvrés",
				"allow_encashment": 0,
				"is_carry_forward": 1,
				"include_holiday": 0,
				"is_compensatory": 0,
				"max_leaves_allowed": 25,
				"allow_negative": 1,
				"is_earned_leave": 1,
				"earned_leave_frequency": "Congés payés sur jours ouvrés",
				"period_start_day": 1,
				"period_start_month": 6,
				"period_end_day": 31,
				"period_end_month": 5
			},
		]
		for leave_type in leave_types:
				doc = frappe.get_doc(leave_type)
				doc.insert(ignore_permissions=True, ignore_if_duplicate=True)

		last_holiday_list = None
		for year in [2018, 2019, 2020, 2021, 2022]:
			bank_holidays = [{"holiday_date": value, "description": key} for key, value in get_french_bank_holidays(year).items()]
			holiday_list = make_holiday_list(
				f"_Test France Holiday List {year}", f"{year}-01-01", f"{year}-12-31", bank_holidays
			)
			holiday_list.weekly_off = "Saturday"
			holiday_list.get_weekly_off_dates()
			holiday_list.weekly_off = "Sunday"
			holiday_list.get_weekly_off_dates()
			holiday_list.replaces_holiday_list = last_holiday_list
			holiday_list.save()

			last_holiday_list = holiday_list.name

		for contract_type in ["Temps plein", "Temps partiel"]:
			frappe.get_doc({
				"doctype": "Employment Contract Type",
				"employment_contract_type": contract_type,
			}).insert(ignore_if_duplicate=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def setUp(self):
		self.employee = make_employee("testfranceleavesemp@example.com", company="_Test Company")

		frappe.db.delete("Leave Ledger Entry")
		frappe.db.delete("Leave Allocation")
		frappe.db.delete("Leave Application")

	def test_conges_payes_sur_jours_ouvrables(self):
		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 7,
			"thursday": 7,
			"friday": 7
		})
		contract.append("leave_types", {
			"leave_type": "Congés Payés sur jours ouvrables"
		})
		contract.insert(ignore_if_duplicate=True)

		self.calculate_leaves("Congés Payés sur jours ouvrables", 2.5, 30)

	def test_conges_payes_sur_jours_ouvres(self):
		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 7,
			"thursday": 7,
			"friday": 7
		})
		contract.append("leave_types", {
			"leave_type": "Congés Payés sur jours ouvrés"
		})
		contract.insert(ignore_if_duplicate=True)

		self.calculate_leaves("Congés Payés sur jours ouvrés", 2.08, 25)


	def test_conges_payes_sur_jours_ouvrables_temps_partiel(self):
		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 0,
			"thursday": 0,
			"friday": 0
		})
		contract.append("leave_types", {
			"leave_type": "Congés Payés sur jours ouvrables"
		})
		contract.insert(ignore_if_duplicate=True)

		self.calculate_leaves("Congés Payés sur jours ouvrables", 2.5, 30)


	def test_conges_payes_sur_jours_ouvres_temps_partiel(self):
		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 0,
			"thursday": 0,
			"friday": 0
		}).insert(ignore_if_duplicate=True)

		contract.append("leave_types", {
			"leave_type": "Congés Payés sur jours ouvrés"
		})

		self.calculate_leaves("Congés Payés sur jours ouvrés", 2.08, 25)


	def calculate_leaves(self, leave_type, monthly, yearly, periods=None):
		current_year = None
		for period in periods or PERIODS:
			if current_year != getdate(period[0]).year:
				frappe.db.set_value("Employee", self.employee, "holiday_list", f"_Test France Holiday List {getdate(period[0]).year}")
				current_year = getdate(period[0]).year

			for date in daterange(getdate(period[0]), getdate(period[1])):
				frappe.flags.current_date = date
				allocate_earned_leaves(date)
				leave_allocations = get_leave_allocations_for_employee(date, self.employee, leave_type)
				if not leave_allocations:
					continue
				leave_allocation = frappe.get_doc("Leave Allocation", leave_allocations[0])
				if date == get_last_day(date):
					if date == getdate(period[1]):
						self.assertEqual(flt(leave_allocation.total_leaves_allocated - leave_allocation.unused_leaves, 2), yearly)
					else:
						self.assertEqual(flt(leave_allocation.total_leaves_allocated - leave_allocation.unused_leaves, 2), flt(monthly * month_diff(date, getdate(period[0])), 2))


	def test_leave_application_jours_ouvrables(self):
		approver = make_employee("testfranceleavesappro@example.com", company="_Test Company")
		frappe.db.set_value("Employee", self.employee, "leave_approver", approver)

		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 0,
			"thursday": 0,
			"friday": 0
		})
		contract.append("leave_types", {
			"leave_type": "Congés Payés sur jours ouvrables"
		})
		contract.insert(ignore_if_duplicate=True)

		self.calculate_leaves("Congés Payés sur jours ouvrables", 2.5, 30, PERIODS[1:2])

		leaves = [
			("2019-08-02", "2019-08-12"),
			("2019-10-30", "2019-11-04"),
			("2019-12-31", "2020-01-06"),
			("2020-04-03", "2020-04-13"),
		]

		total_leaves = {
			0: 6,
			1: 2,
			2: 3,
			3: 6
		}
		for index, leave in enumerate(leaves):
			doc = frappe.get_doc({
				"doctype": "Leave Application",
				"employee": self.employee,
				"leave_type": "Congés Payés sur jours ouvrables",
				"from_date": leave[0],
				"to_date": leave[1],
				"leave_approver": frappe.db.get_value("Employee", approver, "user_id")
			}).insert()
			self.assertEqual(total_leaves.get(index), doc.total_leave_days)

	def test_leave_application_jours_ouvres(self):
		approver = make_employee("testfranceleavesappro@example.com", company="_Test Company")
		frappe.db.set_value("Employee", self.employee, "leave_approver", approver)

		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 0,
			"thursday": 0,
			"friday": 0
		})
		contract.append("leave_types", {
			"leave_type": "Congés Payés sur jours ouvrés"
		})
		contract.insert(ignore_if_duplicate=True)


		self.calculate_leaves("Congés Payés sur jours ouvrés", 2.08, 25, PERIODS[1:2])

		leaves = [
			("2019-08-02", "2019-08-12"),
			("2019-10-30", "2019-11-04"),
			("2019-12-31", "2020-01-06"),
			("2020-04-03", "2020-04-13"),
		]

		total_leaves = {
			0: 5,
			1: 1,
			2: 2,
			3: 5
		}
		for index, leave in enumerate(leaves):
			doc = frappe.get_doc({
				"doctype": "Leave Application",
				"employee": self.employee,
				"leave_type": "Congés Payés sur jours ouvres",
				"from_date": leave[0],
				"to_date": leave[1],
				"leave_approver": frappe.db.get_value("Employee", approver, "user_id")
			}).insert()
			self.assertEqual(total_leaves.get(index), doc.total_leave_days)


	def test_carry_forward(self):
		approver = make_employee("testfranceleavesappro@example.com", company="_Test Company")
		frappe.db.set_value("Employee", self.employee, "leave_approver", approver)
		leave_type = "Congés Payés sur jours ouvrables"

		contract = frappe.get_doc({
			"doctype": "Employment Contract",
			"employee": self.employee,
			"company": "_Test Company",
			"date_of_joining": frappe.db.get_value("Employee", self.employee, "date_of_joining"),
			"contract_type": "Temps plein",
			"designation": "Analyst",
			"monday": 7,
			"tuesday": 7,
			"wednesday": 0,
			"thursday": 0,
			"friday": 0
		})
		contract.append("leave_types", {
			"leave_type": leave_type
		})
		contract.insert(ignore_if_duplicate=True)

		leaves = {
			2018: [
				("2018-06-08", "2018-06-18"),
				("2018-08-03", "2018-08-20"),
				("2018-12-31", "2019-01-07"),
			],
			2019: [
				("2019-08-02", "2019-08-12"),
				("2019-10-30", "2019-11-04"),
				("2019-12-31", "2020-01-06"),
				("2020-04-03", "2020-04-13"),
			],
			2020: []
		}

		unused_leaves = {
			2018: 0,
			2019: 9,
			2020: 22,
		}

		current_year = None
		for period in PERIODS[0:3]:
			if current_year != getdate(period[0]).year:
				frappe.db.set_value("Employee", self.employee, "holiday_list", f"_Test France Holiday List {getdate(period[0]).year}")
				current_year = getdate(period[0]).year

			for leave in leaves[current_year]:
				doc = frappe.get_doc({
					"doctype": "Leave Application",
					"employee": self.employee,
					"leave_type": leave_type,
					"from_date": leave[0],
					"to_date": leave[1],
					"leave_approver": frappe.db.get_value("Employee", approver, "user_id")
				}).insert()
				doc.status = "Approved"
				doc.submit()


			self.calculate_leaves(leave_type, 2.5, 30, [period])

			for date in daterange(getdate(period[0]), getdate(period[1])):
				allocate_earned_leaves(date)
				leave_allocations = get_leave_allocations_for_employee(date, self.employee, leave_type)
				if not leave_allocations:
					continue
				leave_allocation = frappe.get_doc("Leave Allocation", leave_allocations[0])

				process_expired_allocation()

			self.assertEqual(leave_allocation.unused_leaves, unused_leaves[current_year])

def get_leave_allocations_for_employee(date, employee, leave_type):
	return frappe.get_all(
		"Leave Allocation",
		filters={
			"from_date": ("<=", date),
			"to_date": (">=", date),
			"employee": employee,
			"docstatus": 1,
			"leave_type": leave_type
		},
		fields=["name", "employee", "from_date", "to_date", "leave_policy_assignment",
			"leave_policy", "company", "leave_type", "new_leaves_allocated",
			"total_leaves_allocated"
		]
		)