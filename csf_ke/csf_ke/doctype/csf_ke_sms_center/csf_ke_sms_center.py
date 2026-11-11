# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.model.document import Document
from frappe.utils import cstr


class CSFKESMSCenter(Document):
	@frappe.whitelist()
	def create_receiver_list(self):
		rec, where_clause = "", ""
		values = {}
		if self.send_to == "All Customer Contact":
			where_clause = """ and dl.link_doctype = 'Customer'
                and cu.unsubscribed = 0
                and char_length(c.mobile_no) > 8
            """

			if self.customer:
				where_clause += (
					""" and dl.link_name = %(customer)s"""
					or " and ifnull(dl.link_name, '') != ''"
				)
				values["customer"] = self.customer

			if self.customer_group:
				where_clause += " and cu.customer_group = %(customer_group)s"
				values["customer_group"] = self.customer_group

			if self.territory:
				where_clause += " and cu.territory = %(territory)s"
				values["territory"] = self.territory

			if self.start_date and self.end_date and self.end_date > self.start_date:
				where_clause += " and si.posting_date between %(start_date)s and %(end_date)s"
				values.update(start_date=self.start_date, end_date=self.end_date)

			elif self.start_date:
				where_clause += " and si.posting_date >= %(start_date)s"
				values["start_date"] = self.start_date

			elif self.end_date:
				where_clause += " and si.posting_date <= %(end_date)s"
				values["end_date"] = self.end_date

		if self.send_to == "All Supplier Contact":
			where_clause = " and dl.link_doctype = 'Supplier'"
			if self.supplier:
				where_clause += (
					""" and dl.link_name = %(supplier)s"""
					or " and ifnull(dl.link_name, '') != ''"
				)
				values["supplier"] = self.supplier

		if self.send_to == "All Sales Partner Contact":
			where_clause = " and dl.link_doctype = 'Sales Partner'"
			if self.sales_partner:
				where_clause += (
					"""and dl.link_name = %(sales_partner)s"""
					or " and ifnull(dl.link_name, '') != ''"
				)
				values["sales_partner"] = self.sales_partner

		if self.send_to == "All Customer Contact":
			rec = frappe.db.sql(
				f"""select distinct(CONCAT(ifnull(c.first_name,''), ' ', ifnull(c.last_name,''))), c.mobile_no
                from `tabContact` c, `tabDynamic Link` dl INNER JOIN `tabCustomer` cu ON dl.link_name = cu.name
                left join `tabSales Invoice` si on cu.name = si.customer_name
                where ifnull(c.mobile_no,'')!='' and
                c.docstatus != 2 and dl.parent = c.name{where_clause}""",
				values,
			)

		elif self.send_to in [
			"All Contact",
			"All Supplier Contact",
			"All Sales Partner Contact",
		]:
			rec = frappe.db.sql(
				f"""select distinct(CONCAT(ifnull(c.first_name,''), ' ', ifnull(c.last_name,''))), c.mobile_no
                from `tabContact` c, `tabDynamic Link` dl
                where ifnull(c.mobile_no,'')!='' and
                c.docstatus != 2 and dl.parent = c.name{where_clause}""",
				values,
			)

		elif self.send_to == "All Lead (Open)":
			query = """select lead_name, mobile_no from `tabLead` where
                ifnull(mobile_no,'')!='' and docstatus != 2 and status='Open'"""

			if self.territory:
				query += " and territory = %(territory)s"
				values["territory"] = self.territory

			if self.start_date and self.end_date and self.start_date > self.end_date:
				query += " and creation between %(start_date)s and %(end_date)s"
				values.update(start_date=self.start_date, end_date=self.end_date)

			elif self.start_date:
				query += " and creation >= %(start_date)s"
				values["start_date"] = self.start_date

			elif self.end_date:
				query += " and creation <= %(end_date)s"
				values["end_date"] = self.end_date

			rec = frappe.db.sql(query, values)

		elif self.send_to == "All Employee (Active)":
			where_clause = (
				self.department and """ and department = %(department)s"""
			) or ""
			where_clause += (self.branch and """ and branch = %(branch)s""") or ""
			values.update(department=self.department, branch=self.branch)

			rec = frappe.db.sql(
				f"""select employee_name, cell_number from
                `tabEmployee` where status = 'Active' and docstatus < 2 and
                ifnull(cell_number,'')!='' {where_clause}""",
				values,
			)

		elif self.send_to == "All Sales Person":
			rec = frappe.db.sql(
				"""select sales_person_name,
                tabEmployee.cell_number from `tabSales Person` left join tabEmployee
                on `tabSales Person`.employee = tabEmployee.name
                where ifnull(tabEmployee.cell_number,'')!=''"""
			)

		rec_list = ""
		for d in rec:
			rec_list += d[0] + " - " + d[1] + "\n"

		self.receiver_list = rec_list

	def get_receiver_nos(self):
		receiver_nos = []
		if self.receiver_list:
			for d in self.receiver_list.split("\n"):
				receiver_no = d
				if "-" in d:
					receiver_no = receiver_no.split("-")[1]
				if receiver_no.strip():
					receiver_nos.append(cstr(receiver_no).strip())
		else:
			msgprint(_("Receiver List is empty. Please create Receiver List"))

		return receiver_nos

	@frappe.whitelist()
	def send_sms(self):
		receiver_list = []
		if not self.message:
			msgprint(_("Please enter message before sending"))

		else:
			receiver_list = self.get_receiver_nos()

		if receiver_list:
			send_sms(receiver_list, cstr(self.message))
