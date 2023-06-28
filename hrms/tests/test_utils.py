import frappe
from frappe.utils import add_months, get_first_day, get_last_day, getdate, now_datetime

from erpnext.setup.doctype.department.department import get_abbreviated_name
from erpnext.setup.utils import enable_all_roles_and_domains


def before_tests():
	frappe.clear_cache()
	# complete setup if missing
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = now_datetime().year
	if not frappe.get_list("Company"):
		setup_complete(
			{
				"currency": "INR",
				"full_name": "Test User",
				"company_name": "Wind Power LLC",
				"timezone": "Asia/Kolkata",
				"company_abbr": "WP",
				"industry": "Manufacturing",
				"country": "India",
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"language": "english",
				"company_tagline": "Testing",
				"email": "test@erpnext.com",
				"password": "test",
				"chart_of_accounts": "Standard",
			}
		)

	enable_all_roles_and_domains()
	frappe.db.commit()  # nosemgrep


def get_first_sunday(holiday_list="Salary Slip Test Holiday List", for_date=None):
	date = for_date or getdate()
	month_start_date = get_first_day(date)
	month_end_date = get_last_day(date)
	first_sunday = frappe.db.sql(
		"""
		select holiday_date from `tabHoliday`
		where parent = %s
			and holiday_date between %s and %s
		order by holiday_date
	""",
		(holiday_list, month_start_date, month_end_date),
	)[0][0]

	return first_sunday


def get_first_day_for_prev_month():
	prev_month = add_months(getdate(), -1)
	prev_month_first = prev_month.replace(day=1)
	return prev_month_first


def create_company(name: str = "_Test Company"):
	if frappe.db.exists("Company", name):
		return frappe.get_doc("Company", name)

	return frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": name,
			"default_currency": "INR",
			"country": "India",
		}
	).insert()


def create_department(name: str, company: str = "_Test Company") -> str:
	docname = get_abbreviated_name(name, company)

	if frappe.db.exists("Department", docname):
		return docname

	department = frappe.new_doc("Department")
	department.update({"doctype": "Department", "department_name": name, "company": "_Test Company"})
	department.insert()
	return department.name