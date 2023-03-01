import click

from hrms.setup import after_install as setup


def after_install():
	try:
		print("Setting up HRMS...")
		setup()

		click.secho("Thank you for installing Dokos HR Management System!", fg="green")

	except Exception as e:
		BUG_REPORT_URL = "https://gitlab.com/dokos/hrms/-/issues"
		click.secho(
			"Installation for HRMS app failed due to an error."
			" Please try re-installing the app or"
			f" report the issue on {BUG_REPORT_URL} if not resolved.",
			fg="bright_red",
		)
		raise e
