import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list
from hrms.regional.france.hr.bank_holidays import get_french_bank_holidays
from hrms.regional.france.setup import setup
from hrms.regional.france.hr.utils import daterange, allocate_earned_leaves

PERIODS = [
	("2018-06-01", "2019-05-31"),
	("2019-06-01", "2020-05-31"),
	("2020-06-01", "2021-05-31"),
	("2021-06-01", "2022-05-31"),
	("2022-06-01", "2023-05-31")
]


class TestFranceLeaves(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		frappe.flags.country = "France"

		setup()

		frappe.db.set_value("HR Settings", None, "calculate_attendances", 1)

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

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_conges_payes_sur_jours_ouvrables(self):
		employee = make_employee("testfranceleavesemp1@example.com", company="_Test Company")

		current_year = None
		for period in PERIODS:
			if current_year != getdate(period[0]).year:
				frappe.db.set_value("Employee", employee, "holiday_list", f"_Test France Holiday List {getdate(period[0]).year}")
				current_year = getdate(period[0]).year

			leave_allocation = frappe.get_doc({
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_type": "Congés Payés",
				"from_date": period[0],
				"to_date": period[1],
				"company": "_Test Company"
			})
			leave_allocation.insert()
			leave_allocation.submit()


			for date in daterange(getdate(period[0]), getdate(period[1])):
				allocate_earned_leaves(date)
				leave_allocation.reload()

				if date == getdate(period[0]):
					self.assertEqual(leave_allocation.total_leaves_allocated, 0)

				if date == getdate(period[1]):
					self.assertEqual(leave_allocation.total_leaves_allocated, 25)

