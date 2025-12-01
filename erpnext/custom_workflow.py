# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, cint, flt
from frappe.utils import get_link_to_form
from hrms.hr.hr_custom_function import get_officiating_employee
from frappe.utils.nestedset import get_ancestors_of


class CustomWorkflow:
	def __init__(self, doc):
		self.doc = doc
		self.new_state = self.doc.workflow_state
		self.old_state = self.doc.get_db_value("workflow_state")

		self.field_map = get_field_map()
		self.doc_approver = self.field_map[self.doc.doctype]
		self.field_list = ["user_id", "employee_name", "designation", "name"]

		### =============== *** =============== *** === NYUTHYUE === *** =============== *** =============== ###
		if self.doc.doctype in (
			"Travel Authorization",
			"Travel Advance",
			"Travel Adjustment",
			"Travel Claim",
			"Employee Advance",
			"Leave Encashment",
		):
			self.employee = frappe.db.get_value(
				"Employee", self.doc.employee, self.field_list
			)
			self.reports_to= frappe.db.get_value(
				"Employee",
				{
					"name": frappe.db.get_value(
						"Employee", self.doc.employee, "reports_to"
					)
				},
				self.field_list,
			)
			if not self.reports_to:
				self.department = frappe.db.get_value(
						"Employee", 
						self.doc.employee, 
						"department"
					)
				if self.department:
					exist_appr=frappe.db.exists("Department","approver" ,self.employee)
					hr_approver=frappe.db.get_single_value('HR Settings','hr_manager')
					email=frappe.db.get_value("Employee", hr_approver, "user_id")
					if not email:
						frappe.throw("HR Manager is not in HR Settings")
					
					self.reports_to=email
					#return
				else:
					frappe.throw(
						"Reports To not set for Employee {}".format(
							self.doc.employee
							if self.doc.employee
							else frappe.db.get_value(
								"Employee", {"user_id", self.doc.owner}, "name"
							)
						)
					)

			self.hr_manager = frappe.db.get_value(
				"Employee",
				frappe.db.get_single_value("HR Settings", "hr_manager"),
				self.field_list,
			)
			if not self.hr_manager:

				frappe.throw("Plesse set HR Manager in HR Settings")
		### =============== *** =============== *** === NYUTHYUE === *** =============== *** =============== ###

		elif self.doc.doctype != "Material Request" and self.doc.doctype not in (
			"Asset Issue Details",
			"Compile Budget",
			"POL Expense",
			"Vehicle Request",
			"Repair And Services",
			"Asset Movement",
			"Budget Reappropiation",
		):
			self.employee = frappe.db.get_value(
				"Employee", self.doc.employee, self.field_list
			)
			self.reports_to = frappe.db.get_value(
				"Employee",
				{
					"name": frappe.db.get_value(
						"Employee", self.doc.employee, "reports_to"
					)
				},
				self.field_list,
			)

			if self.doc.doctype in (
				"Travel Request",
				"Employee Separation",
				"Overtime Application",
			):
				if frappe.db.get_value(
					"Employee", self.doc.employee, "expense_approver"
				):
					self.expense_approver = frappe.db.get_value(
						"Employee",
						{
							"user_id": frappe.db.get_value(
								"Employee", self.doc.employee, "expense_approver"
							)
						},
						self.field_list,
					)
				else:
					pass
					# frappe.throw(
					#     "Expense Approver not set for employee {}".format(
					#         self.doc.employee
					#     )
					# )
			self.supervisors_supervisor = frappe.db.get_value(
				"Employee",
				frappe.db.get_value(
					"Employee",
					frappe.db.get_value("Employee", self.doc.employee, "reports_to"),
					"reports_to",
				),
				self.field_list,
			)
			self.hr_approver = frappe.db.get_value(
				"Employee",
				frappe.db.get_single_value("HR Settings", "hr_approver"),
				self.field_list,
			)
			self.hrgm = frappe.db.get_value(
				"Employee",
				frappe.db.get_single_value("HR Settings", "hr_manager"),
				self.field_list,
			)
			self.ceo = frappe.db.get_value(
				"Employee",
				frappe.db.get_value(
					"Employee",
					{"designation": "Chief Executive Officer", "status": "Active"},
					"name",
				),
				self.field_list,
			)
			# self.pms_appealer  = frappe.db.get_value("Employee", frappe.db.get_single_value("PMS Setting", "approver"), self.field_list)
			# self.dept_approver	= frappe.db.get_value("Employee", frappe.db.get_value("Department", str(frappe.db.get_value("Employee", self.doc.employee, "department")), "approver"), self.field_list)
			# self.gm_approver	= frappe.db.get_value("Employee", frappe.db.get_value("Department",{"department_name":str(frappe.db.get_value("Employee", self.doc.employee, "division"))}, "approver_hod"),self.field_list)

			if self.doc.doctype in ["POL", "Leave Application", "Vehicle Request"]:
				# frappe.throw("hi")
				self.adm_section_manager = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Department Approver",
							{
								"parent": "Administration Section - SMCL",
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					},
					self.field_list,
				)
		if self.doc.doctype == "Asset Movement":
			department = frappe.db.get_value(
				"Employee", self.doc.from_employee, "department"
			)
			if not department:
				frappe.throw("Department not set for {}".format(self.doc.from_employee))
			if department != "CHIEF EXECUTIVE OFFICE - SMCL":
				self.asset_verifier = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Department Approver",
							{
								"parent": department,
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					},
					self.field_list,
				)
				if not self.asset_verifier:
					self.asset_verifier = frappe.get_value(
						"Department", department, "approver"
					)
			else:
				self.asset_verifier = frappe.db.get_value(
					"Employee",
					frappe.db.get_value(
						"Employee",
						{"designation": "Chief Executive Officer", "status": "Active"},
						"name",
					),
					self.field_list,
				)

		if self.doc.doctype in ("POL Expense"):
			department = frappe.db.get_value(
				"Employee", {"user_id": self.doc.owner}, "department"
			)
			section = frappe.db.get_value(
				"Employee", {"user_id": self.doc.owner}, "section"
			)
			if section in (
				"Chunaikhola Dolomite Mines - SMCL",
				"Samdrup Jongkhar - SMCL",
			):
				self.pol_approver = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Department Approver",
							{
								"parent": section,
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					},
					self.field_list,
				)
			else:
				self.pol_approver = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Department Approver",
							{
								"parent": department,
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					},
					self.field_list,
				)
		if self.doc.doctype in ("Budget Reappropiation"):
			department = frappe.db.get_value(
				"Employee", {"user_id": self.doc.owner}, "department"
			)
			section = frappe.db.get_value(
				"Employee", {"user_id": self.doc.owner}, "section"
			)
			self.ceo = frappe.db.get_value(
				"Employee",
				frappe.db.get_value(
					"Employee",
					{"designation": "Chief Executive Officer", "status": "Active"},
					"name",
				),
				self.field_list,
			)
			if section in (
				"Chunaikhola Dolomite Mines - SMCL",
				"Samdrup Jongkhar - SMCL",
			):
				self.budget_reappropiation_approver = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Department Approver",
							{
								"parent": section,
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					},
					self.field_list,
				)
			else:
				self.budget_reappropiation_approver = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Department Approver",
							{
								"parent": department,
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					},
					self.field_list,
				)
			if not self.budget_reappropiation_approver:
				frappe.throw(
					"No employee found for user id(expense approver) {}".format(
						frappe.db.get_value(
							"Department Approver",
							{
								"parent": department,
								"parentfield": "expense_approvers",
								"idx": 1,
							},
							"approver",
						)
					)
				)

		if self.doc.doctype == "Material Request":
			self.user_supervisor = frappe.db.get_value(
				"Employee",
				frappe.db.get_value(
					"Employee", {"user_id": self.doc.owner}, "reports_to"
				),
				self.field_list,
			)

		if self.doc.doctype == "Employee Benefits":
			self.hrgm = frappe.db.get_value(
				"Employee",
				frappe.db.get_single_value("HR Settings", "hr_manager"),
				self.field_list,
			)

		if self.doc.doctype == "Repair And Services":
			self.expense_approver = frappe.db.get_value(
				"Employee",
				{
					"user_id": frappe.db.get_value(
						"Employee", {"user_id": self.doc.owner}, "expense_approver"
					)
				},
				self.field_list,
			)
			self.hrgm = frappe.db.get_value(
				"Employee",
				frappe.db.get_single_value("HR Settings", "hrgm"),
				self.field_list,
			)

		if self.doc.doctype == "Vehicle Request":
			department = frappe.db.get_value(
				"Employee", self.doc.employee, "department"
			)
			if not department:
				frappe.throw("set department for employee in employee master")
			if frappe.db.get_value("Employee", self.doc.employee, "expense_approver"):
				self.expense_approver = frappe.db.get_value(
					"Employee",
					{
						"user_id": frappe.db.get_value(
							"Employee", self.doc.employee, "expense_approver"
						)
					},
					self.field_list,
				)
			else:
				frappe.throw(
					"Expense Approver not set for employee {}".format(self.doc.employee)
				)
			self.vehicle_mto = frappe.db.get_value(
				"Employee",
				{
					"user_id": frappe.db.get_value(
						"Department", department, "approver_id"
					)
				},
				self.field_list,
			)

		self.login_user = frappe.db.get_value(
			"Employee", {"user_id": frappe.session.user}, self.field_list
		)

		if not self.login_user and frappe.session.user not in (
			"Administrator",
			"sonam.zangmo@thimphutechpark.bt",
		):
			if "PERC Member" in frappe.get_roles(frappe.session.user):
				return
			frappe.throw("{0} is not added as the employee".format(frappe.session.user))

	def apply_workflow(self):
		# frappe.throw('hi')

		if (self.doc.doctype not in self.field_map) or not frappe.db.exists(
			"Workflow", {"document_type": self.doc.doctype, "is_active": 1}
		):
			return

		if self.doc.doctype == "Leave Application":
			self.leave_application()

		elif self.doc.doctype == "Travel Request":
			self.travel_request()

		### =============== *** =============== *** === NYUTHYUE === *** =============== *** =============== ###
		elif self.doc.doctype == "Leave Encashment":
			self.leave_encashment()
		elif self.doc.doctype == "Employee Advance":
			self.employee_advance()
		elif self.doc.doctype == "Travel Authorization":
			self.travel_authorization()
		elif self.doc.doctype == "Travel Claim":
			self.travel_claim()
		elif self.doc.doctype == "Travel Advance":
			self.travel_advance()
		elif self.doc.doctype == "Travel Adjustment":
			self.travel_adjustment()
		### =============== *** =============== *** === NYUTHYUE === *** =============== *** =============== ###

		elif self.doc.doctype == "Vehicle Request":
			self.vehicle_request()
		elif self.doc.doctype == "Repair And Services":
			self.repair_services()
		elif self.doc.doctype == "Overtime Application":
			self.overtime_application()
		elif self.doc.doctype == "Material Request":
			self.material_request()
		elif self.doc.doctype == "Employee Advance":
			self.employee_advance()
		elif self.doc.doctype == "Employee Benefit Claim":
			self.employee_benefit_claim()
		elif self.doc.doctype == "POL Expense":
			self.pol_expenses()
		elif self.doc.doctype == "Budget Reappropiation":
			self.budget_reappropiation()
		elif self.doc.doctype == "Employee Separation":
			self.employee_separation()
		elif self.doc.doctype == "Employee Benefits":
			self.employee_benefits()
		elif self.doc.doctype == "Coal Raising Payment":
			self.coal_raising_payment()
		elif self.doc.doctype == "POL":
			self.pol()
		elif self.doc.doctype in ("Asset Issue Details", "Project Capitalization"):
			self.asset()
		elif self.doc.doctype == "Compile Budget":
			self.compile_budget()
		elif self.doc.doctype == "Asset Movement":
			self.asset_movement()
		elif self.doc.doctype == "Target Set Up":
			self.target_set_up_and_review()
		elif self.doc.doctype == "Review":
			self.target_set_up_and_review()
		elif self.doc.doctype == "Performance Evaluation":
			self.performance_evaluation()
		elif self.doc.doctype == "SWS Application":
			self.sws_application()
		elif self.doc.doctype == "SWS Membership":
			self.sws_membership()
		elif self.doc.doctype == "Contract Renewal Application":
			self.contract_renewal_application()
		elif self.doc.doctype == "Promotion Application":
			self.promotion_application()
		elif self.doc.doctype == "PMS Appeal":
			self.pms_appeal()
		else:
			frappe.throw(_("Workflow not defined for {}").format(self.doc.doctype))

	def set_approver(self, approver_type):
		if approver_type == "Supervisor":
			if not self.reports_to:
				frappe.throw(
					"Reports To not set for Employee {}".format(
						self.doc.employee
						if self.doc.employee
						else frappe.db.get_value(
							"Employee", {"user_id", self.doc.owner}, "name"
						)
					)
				)
			officiating = get_officiating_employee(self.reports_to[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.reports_to[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.reports_to[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.reports_to[2]
			)

		elif approver_type == "User Supervisor":
			officiating = get_officiating_employee(self.user_supervisor[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.user_supervisor[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.user_supervisor[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.user_supervisor[2]
			)

		elif approver_type == "User Approver":
			officiating = get_officiating_employee(self.user_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.user_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.user_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.user_approver[2]
			)

		elif approver_type == "POL Approver":
			officiating = get_officiating_employee(self.pol_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.pol_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.pol_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.pol_approver[2]
			)

		elif approver_type == "Asset Verifier":
			officiating = get_officiating_employee(self.asset_verifier[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.asset_verifier[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.asset_verifier[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.asset_verifier[2]
			)

		elif approver_type == "Imprest Verifier":
			officiating = get_officiating_employee(self.imprest_verifier[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.imprest_verifier[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.imprest_verifier[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.imprest_verifier[2]
			)

		elif approver_type == "Imprest Approver":
			officiating = get_officiating_employee(self.imprest_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.imprest_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.imprest_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.imprest_approver[2]
			)

		elif approver_type == "Supervisors Supervisor":
			officiating = get_officiating_employee(self.supervisors_supervisor[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.supervisors_supervisor[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.supervisors_supervisor[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.supervisors_supervisor[2]
			)

		elif approver_type == "Fleet Manager":
			officiating = get_officiating_employee(self.fleet_mto[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.fleet_mto[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.fleet_mto[1]
			)
			# vars(self.doc)[self.doc_approver[2]] = officiating[2] if officiating else self.fleet_mto[2]

		elif approver_type == "Fleet MTO":
			officiating = get_officiating_employee(self.vehicle_mto[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.vehicle_mto[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.vehicle_mto[1]
			)
			# vars(self.doc)[self.doc_approver[2]] = officiating[2] if officiating else self.vehicle_mto[2]

		elif approver_type == "Project Manager":
			if self.project_manager == None:
				frappe.throw(
					"""No Project Manager set in Project Definition <a href="#Form/Project%20Definition/{0}">{0}</a>""".format(
						frappe.db.get_value(
							"Project", self.doc.reference_name, "project_definition"
						)
					)
				)
			officiating = get_officiating_employee(self.project_manager[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.project_manager[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.project_manager[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.project_manager[2]
			)

		elif approver_type == "HR":
			officiating = get_officiating_employee(self.hr_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.hr_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.hr_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.hr_approver[2]
			)

		elif approver_type == "HR Manager":
			officiating = get_officiating_employee(self.hr_manager[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.hr_manager[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.hr_manager[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.hr_manager[2]
			)

		elif approver_type == "HRGM":
			officiating = get_officiating_employee(self.hrgm[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.hrgm[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.hrgm[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.hrgm[2]
			)

		elif approver_type == "Warehouse Manager":
			officiating = get_officiating_employee(self.warehouse_manager[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.warehouse_manager[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.warehouse_manager[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.warehouse_manager[2]
			)

		elif approver_type == "Manager Power":
			officiating = get_officiating_employee(self.power_section_manager[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.power_section_manager[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.power_section_manager[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.power_section_manager[2]
			)

		elif approver_type == "ADM":
			officiating = get_officiating_employee(self.adm_section_manager[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.adm_section_manager[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.adm_section_manager[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.adm_section_manager[2]
			)

		elif approver_type == "GMM":
			officiating = get_officiating_employee(self.gm_marketing[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.gm_marketing[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.gm_marketing[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.gm_marketing[2]
			)

		elif approver_type == "GMO":
			officiating = get_officiating_employee(self.gmo[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.gmo[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.gmo[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.gmo[2]
			)

		elif approver_type == "Regional Director":
			officiating = get_officiating_employee(self.regional_director[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.regional_director[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.regional_director[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.regional_director[2]
			)

		elif approver_type == "Department Head":
			officiating = get_officiating_employee(self.dept_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.dept_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.dept_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.dept_approver[2]
			)

		elif approver_type == "GM":
			# frappe.msgprint(str(self.gm_approver))
			officiating = get_officiating_employee(self.gm_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.gm_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.gm_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.gm_approver[2]
			)

		elif approver_type == "CEO":
			officiating = get_officiating_employee(self.ceo[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.ceo[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.ceo[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.ceo[2]
			)

		elif approver_type == "GM":
			officiating = get_officiating_employee(self.reports_to[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.reports_to[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.reports_to[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.reports_to[2]
			)

		elif approver_type == "PMS Appealer":
			officiating = get_officiating_employee(self.reports_to[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.pms_appealer[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.pms_appealer[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.pms_appealer[2]
			)

		elif approver_type == "Budget Reappropiation":
			officiating = get_officiating_employee(
				self.budget_reappropiation_approver[3]
			)
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0]
				if officiating
				else self.budget_reappropiation_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1]
				if officiating
				else self.budget_reappropiation_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2]
				if officiating
				else self.budget_reappropiation_approver[2]
			)

		elif approver_type == "Approver":
			self.doc.leave_approver = self.doc.leave_approver
		elif approver_type == "HR User":
			officiating = get_officiating_employee(self.hr_user_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.hr_user_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.hr_user_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.hr_user_approver[2]
			)

		elif approver_type == "Accounts User":
			officiating = get_officiating_employee(self.accounts_user_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.accounts_user_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.accounts_user_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.accounts_user_approver[2]
			)

		elif approver_type == "Accounts Manager":
			officiating = get_officiating_employee(self.accounts_manager_approver[3])
			if officiating:
				officiating = frappe.db.get_value(
					"Employee", officiating[0].officiating_employee, self.field_list
				)
			vars(self.doc)[self.doc_approver[0]] = (
				officiating[0] if officiating else self.accounts_manager_approver[0]
			)
			vars(self.doc)[self.doc_approver[1]] = (
				officiating[1] if officiating else self.accounts_manager_approver[1]
			)
			vars(self.doc)[self.doc_approver[2]] = (
				officiating[2] if officiating else self.accounts_manager_approver[2]
			)

		else:
			frappe.throw(_("Invalid approver type for Workflow"))

	def set_verifier(self, approver_type):
		if approver_type == "Verifier":
			self.doc.verifier = self.doc.reports_to

	def leave_application(self):
		state = self.new_state.lower()
		user = frappe.session.user

		if state == "draft":
			if user != self.doc.owner:
				frappe.throw(f"Only {self.doc.owner} can apply this leave")

		elif state == "waiting for verification":
			if user != self.doc.owner:
				frappe.throw(
					f"Only {self.doc.owner} can move leave to Waiting for Verification"
				)
			#self.set_verifier("Verifier")

		elif state == "waiting approval":
			if user != self.doc.reports_to:
				frappe.throw(
					f"Only {self.doc.reports_to} have permission to move leave to Waiting Approval"
				)
			# assign leave approver
			#self.set_approver("Approver")

		# Approved
		elif state == "approved":
			if user != self.doc.leave_approver:
				frappe.throw(
					f"Only {self.doc.leave_approver}  have permission to approve this leave"
				)

		# Rejected
		elif state == "rejected":
			if user not in [self.doc.verifier, self.doc.leave_approver]:
				frappe.throw(
					f"Only {self.doc.verifier} or {self.doc.leave_approver} can reject this leave"
				)

		# Cancelled
		elif state == "cancelled":
			if user != self.doc.hr_user:
				frappe.throw(f"Only HR User can cancel leave")

		# Any other invalid state
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))

	### =============== *** =============== *** === NYUTHYUE === *** =============== *** =============== ###
	def leave_encashment(self):
		if (
			self.new_state
			and self.old_state
			and self.new_state.lower() == self.old_state.lower()
		):
			return

		elif self.new_state.lower() in ("Draft".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))

		elif self.new_state.lower() == ("Waiting Approval".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Forward this Request.")
			#self.set_approver("HR Manager")

		elif self.new_state.lower() == ("Approved".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Approved this Request.")

		elif self.new_state.lower() == ("Rejected".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Reject this Request.")
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))

	def travel_authorization(self):
		state = self.new_state.lower()
		user = frappe.session.user

		if state == "draft":
			if user != self.doc.owner:
				frappe.throw(
					f"Only {self.doc.owner} can apply this travel authorization"
				)
		elif state == "waiting for verification":
			if user != self.doc.owner:
				frappe.throw(
					f"Only {self.doc.owner} can move travel authorization to Waiting for Verification"
				)
		elif state == "waiting approval":
			if user != self.doc.reports_to:
				frappe.throw(
					f"Only {self.doc.reports_to} have permission to move to Waiting Approval"
				)
		elif state == "approved":
			if user != self.doc.approver:
				frappe.throw(
					f"Only {self.doc.approver}  have permission to approve this leave"
				)

		# Rejected
		elif state == "rejected":
			if user not in [self.doc.reports_to, self.doc.approver]:
				frappe.throw(
					f"Only {self.doc.reports_to} or {self.doc.approver} can reject this leave"
				)

		# Cancelled
		elif state == "cancelled":
			if user != self.doc.hr_user:
				frappe.throw(f"Only HR User can cancel leave")

		# Any other invalid state
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))
	
	def employee_separation(self):
		
		if (
			self.new_state
			and self.old_state
			and self.new_state.lower() == self.old_state.lower()
		):
			return

		elif self.new_state.lower() in ("Waiting for Verification".lower()):
			
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))

	def travel_claim(self):
		if (
			self.new_state
			and self.old_state
			and self.new_state.lower() == self.old_state.lower()
		):
			return

		elif self.new_state.lower() in ("Draft".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))
		# elif self.new_state.lower() == ("Waiting for Verification".lower()):
		# 	if "HR User" not in frappe.get_roles(frappe.session.user):
		# 		if self.doc.approver != frappe.session.user:
		# 			frappe.throw("Only {} can Approve this request".format(self.doc.approver_name))
		# elif self.new_state.lower() == ("Waiting for Finance Verification".lower()):
		# 	if "Accounts User" not in frappe.get_roles(frappe.session.user):
		# 		if self.doc.approver != frappe.session.user:
		# 			frappe.throw("Only {} can Approve this request".format(self.doc.approver_name))
		# elif self.new_state.lower() == ("Waiting Recommendation".lower()):
		# 	if "Accounts Manager" not in frappe.get_roles(frappe.session.user):
		# 		if self.doc.approver != frappe.session.user:
		# 			frappe.throw("Only {} can Approve this request".format(self.doc.approver_name))
		# elif self.new_state.lower() == ("Waiting Approval".lower()):
		# 	if "Approver" not in frappe.get_roles(frappe.session.user):
		# 		if self.doc.approver != frappe.session.user:
		# 			frappe.throw("Only {} can Approve this request".format(self.doc.approver_name))
		else:
			return
			#frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))

	def travel_advance(self):
		if (
			self.new_state
			and self.old_state
			and self.new_state.lower() == self.old_state.lower()
		):
			return

		elif self.new_state.lower() in ("Draft".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))

		elif self.new_state.lower() == ("Waiting for Verification".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))
			self.set_approver("Supervisor")

		elif self.new_state.lower() == ("Waiting HR Approval".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Forward this Request.")
			self.set_approver("HR Manager")

		elif self.new_state.lower() == ("Approved".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Approved this Request.")

		elif self.new_state.lower() == ("Rejected".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Reject this Request.")
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))

	def travel_adjustment(self):
		if (
			self.new_state
			and self.old_state
			and self.new_state.lower() == self.old_state.lower()
		):
			return

		elif self.new_state.lower() in ("Draft".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))

		elif self.new_state.lower() == ("Waiting for Verification".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this Request".format(self.doc.owner))

		elif self.new_state.lower() == ("Waiting Approval".lower()):
			if frappe.session.user != self.doc.reports_to:
				frappe.throw("Only {} can apply this Request".format(self.doc.reports_to))
		

		
		elif self.new_state.lower() == ("Approved".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Approved this Request.")

		elif self.new_state.lower() == ("Rejected".lower()):
			if frappe.session.user != self.doc.approver:
				frappe.throw(f"Only {self.doc.approver} can Reject this Request.")
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))

	### =============== *** =============== *** === NYUTHYUE === *** =============== *** =============== ###

	def overtime_application(self):
		if self.new_state.lower() in ("Draft".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw("Only {} can apply this leave".format(self.doc.owner))

		elif self.new_state.lower() == ("Waiting Approval".lower()):
			self.set_approver("Supervisor")

		elif self.new_state.lower() == ("Approved".lower()):
			if frappe.session.user != self.doc.ot_approver:
				frappe.throw(
					f"Only {self.doc.ot_approver} can Approve this Overtime Application."
				)

		elif self.new_state.lower() == ("Rejected".lower()):
			if frappe.session.user != self.doc.ot_approver:
				frappe.throw(
					f"Only {self.doc.ot_approver} can Reject this Overtime Application."
				)
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))

	def material_request(self):
		if self.new_state.lower() in ("Draft".lower()):
			if frappe.session.user != self.doc.owner:
				frappe.throw(
					"Only {} can apply this Material Request".format(self.doc.owner)
				)

		elif self.new_state.lower() == ("Waiting For Verification".lower()):
			self.set_approver("User Supervisor")
		elif self.new_state.lower() == ("Waiting For Approval".lower()):
			if self.doc.material_request_type == "Purchase":
				frappe.throw("Contact Admin with this regards")
		elif self.new_state.lower() == ("Approved".lower()):
			# if self.doc.material_request_type =="Purchase" and frappe.session.user != self.doc.approver:
			# 	frappe.throw(f"Only {self.doc.approver} can Approved this Material Request")
			pass
		elif self.new_state.lower() == ("Rejected".lower()):
			# if self.doc.material_request_type =="Purchase" and frappe.session.user != self.doc.approver:
			# 	frappe.throw(f"Only {self.doc.approver} can reject this Material Request")
			pass
		else:
			frappe.throw(_("Invalid Workflow State {}").format(self.doc.workflow_state))


class NotifyCustomWorkflow:
	def __init__(self, doc):
		self.doc = doc
		self.old_state = self.doc.get_db_value("workflow_state")
		self.new_state = self.doc.workflow_state
		self.field_map = get_field_map()
		self.doc_approver = self.field_map[self.doc.doctype]
		self.field_list = ["user_id", "employee_name", "designation", "name"]
		if self.doc.doctype not in (
			"Material Request",
			"Asset Issue Details",
			"Project Capitalization",
			"POL Expense",
		):
			self.employee = frappe.db.get_value(
				"Employee", self.doc.employee, self.field_list
			)
		else:
			self.employee = frappe.db.get_value(
				"Employee", {"user_id": self.doc.owner}, self.field_list
			)

	def notify_employee(self):
		if self.doc.doctype not in (
			"Material Request",
			"Asset Issue Details",
			"Repair And Services",
			"Project Capitalization",
			"POL Expense",
		):
			employee = frappe.get_doc("Employee", self.doc.employee)
		else:
			employee = frappe.get_doc(
				"Employee",
				frappe.db.get_value("Employee", {"user_id": self.doc.owner}, "name"),
			)
		if not employee.user_id:
			return

		parent_doc = frappe.get_doc(self.doc.doctype, self.doc.name)
		args = parent_doc.as_dict()

		if self.doc.doctype == "Leave Application":
			template = frappe.db.get_single_value(
				"HR Settings", "leave_application_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Leave Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Leave Encashment":
			template = frappe.db.get_single_value(
				"HR Settings", "encashment_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Encashment Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Salary Advance":
			template = frappe.db.get_single_value(
				"HR Settings", "advance_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Advance Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Travel Request":
			template = frappe.db.get_single_value(
				"HR Settings", "authorization_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Authorization Status Notification in HR Settings."
					)
				)
				return

		elif self.doc.doctype == "Travel Authorization":
			template = frappe.db.get_single_value(
				"HR Settings", "travel_authorization_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Authorization Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Travel Claim":
			template = frappe.db.get_single_value(
				"HR Settings", "travel_claim_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Authorization Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Overtime Application":
			template = frappe.db.get_single_value(
				"HR Settings", "overtime_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Overtime Status Notification in HR Settings."
					)
				)
				return

		elif self.doc.doctype == "Employee Benefits":
			template = frappe.db.get_single_value(
				"HR Settings", "benefits_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Employee Benefits Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Employee Separation":
			template = frappe.db.get_single_value(
				"HR Settings", "employee_separation_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Employee Separation Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Employee Separation Clearance":
			template = frappe.db.get_single_value(
				"HR Settings",
				"employee_separation_Clearance_status_notification_template",
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Employee Separation Clearance Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Employee Transfer":
			template = frappe.db.get_single_value(
				"HR Settings", "employee_transfer_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Employee Separation Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "POL Expense":
			template = frappe.db.get_single_value(
				"Maintenance Settings", "pol_expense_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for POL Expense Status Notification in Maintenance Settings."
					)
				)
				return
				# added by karma
		elif self.doc.doctype == "Imprest Recoup":
			template = frappe.db.get_single_value(
				"HR Settings", "imprest_recoup_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Imprest Recoup Status Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Material Request":
			template = frappe.db.get_single_value(
				"HR Settings", "material_request_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Material Request Status Notification in HR Settings."
					)
				)
				return

		elif self.doc.doctype == "Asset Issue Details":
			template = frappe.db.get_single_value(
				"Asset Settings", "asset_issue_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Asset Issue Status Notification in Asset Settings."
					)
				)
				return
		elif self.doc.doctype == "Project Capitalization":
			template = frappe.db.get_single_value(
				"Asset Settings", "asset_status_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Asset Status Notification in Asset Settings."
					)
				)
				return
		else:
			template = ""

		if not template:
			frappe.msgprint(
				_("Please set default template for {}.").format(self.doc.doctype)
			)
			return
		email_template = frappe.get_doc("Email Template", template)
		message = frappe.render_template(email_template.response, args)
		if employee:
			self.notify(
				{
					# for post in messages
					"message": message,
					"message_to": employee.user_id,
					# for email
					"subject": email_template.subject,
					"notify": "employee",
				}
			)

	def notify_approver(self):
		if self.doc.get(self.doc_approver[0]):
			parent_doc = frappe.get_doc(self.doc.doctype, self.doc.name)
			args = parent_doc.as_dict()
			args["workflow_state"] = self.new_state
			frappe.msgprint(str(self.new_state))
			if self.doc.doctype == "Leave Application":
				template = frappe.db.get_single_value(
					"HR Settings", "leave_application_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Leave Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Leave Encashment":
				template = frappe.db.get_single_value(
					"HR Settings", "encashment_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Encashment Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Salary Advance":
				template = frappe.db.get_single_value(
					"HR Settings", "advance_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Advance Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Travel Request":
				template = frappe.db.get_single_value(
					"HR Settings", "authorization_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Authorization Approval Notification in HR Settings."
						)
					)
					return

			elif self.doc.doctype == "Travel Authorization":
				template = frappe.db.get_single_value(
					"HR Settings", "travel_authorization_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Authorization Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Travel Claim":
				template = frappe.db.get_single_value(
					"HR Settings", "travel_claim_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Travel Claim Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Overtime Application":
				template = frappe.db.get_single_value(
					"HR Settings", "overtime_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Overtime Approval Notification in HR Settings."
						)
					)
					return

			elif self.doc.doctype == "Employee Benefits":
				template = frappe.db.get_single_value(
					"HR Settings", "benefits_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Employee Benefits Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Employee Transfer":
				template = frappe.db.get_single_value(
					"HR Settings", "employee_transfer_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Employee Benefits Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Employee Separation":
				template = frappe.db.get_single_value(
					"HR Settings", "employee_separation_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Employee Separation Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Employee Separation Clearance":
				template = frappe.db.get_single_value(
					"HR Settings",
					"employee_separation_clearance_approval_notification_template",
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Employee Separation Clearance Approval Notification in HR Settings."
						)
					)
					return
					# added by karma
			elif self.doc.doctype == "Imprest Recoup":
				template = frappe.db.get_single_value(
					"HR Settings", "imprest_recoup_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Imprest Recoup Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "POL Expense":
				template = frappe.db.get_single_value(
					"Maintenance Settings", "pol_expense_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for POL Expense Approval Notification in Maintenance Settings."
						)
					)
					return
			elif self.doc.doctype == "Repair And Services":
				template = frappe.db.get_single_value(
					"Maintenance Settings",
					"repair_and_services_approval_notification_template",
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Repair And Services Approval Notification in Maintenance Settings."
						)
					)
					return
			elif self.doc.doctype == "POL":
				template = frappe.db.get_single_value(
					"Maintenance Settings", "pol_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for POL Approval Notification in Maintenance Settings."
						)
					)
					return
			elif self.doc.doctype == "Material Request":
				template = frappe.db.get_single_value(
					"HR Settings", "material_request_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Material Request Approval Notification in HR Settings."
						)
					)
					return

			elif self.doc.doctype == "Asset Issue Details":
				template = frappe.db.get_single_value(
					"Asset Settings", "asset_issue_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Asset Issue Approval Notification in Asset Settings."
						)
					)
					return

			elif self.doc.doctype == "Project Capitalization":
				template = frappe.db.get_single_value(
					"Asset Settings", "asset_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Asset Approval Notification in Asset Settings."
						)
					)
					return
			else:
				template = ""

			if not template:
				frappe.msgprint(
					_("Please set default template for {}.").format(self.doc.doctype)
				)
				return
			email_template = frappe.get_doc("Email Template", template)
			message = frappe.render_template(email_template.response, args)
			self.notify(
				{
					# for post in messages
					"message": message,
					"message_to": self.doc.get(self.doc_approver[0]),
					# for email
					"subject": email_template.subject,
				}
			)

	def notify_verifier(self):
		verifier_email = self.doc.get("verifier") or self.doc.get("reports_to")

		if not verifier_email:
			frappe.throw(_("Verifier not assigned for this document"))

		# ✅ Use the current in-memory doc (not refetch from DB)
		self.doc.workflow_state = self.new_state
		args = self.doc.as_dict()
		args["workflow_state"] = self.new_state
		frappe.msgprint(str(self.new_state))

		# ✅ Pick email template
		if self.doc.doctype == "Leave Application":
			template = frappe.db.get_single_value(
				"HR Settings", "leave_application_approval_notification_template"
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Leave Approval Notification in HR Settings."
					)
				)
				return
		elif self.doc.doctype == "Travel Authorization":
			template = frappe.db.get_single_value(
				"HR Settings",
				"travel_authorization_approval_notification_template",
			)
			if not template:
				frappe.msgprint(
					_(
						"Please set default template for Travel Authorization Approval Notification HR Settings."
					)
				)
				return
		else:
			template = ""

		if not template:
			frappe.msgprint(
				_("Please set default template for {}.").format(self.doc.doctype)
			)
			return

		email_template = frappe.get_doc("Email Template", template)
		message = frappe.render_template(email_template.response, args)

		# ✅ Send notification
		self.notify(
			{
				"message": message,
				"message_to": verifier_email,
				"subject": email_template.subject,
			}
		)

	def notify_hr_users(self):
		receipients = []
		email_group = frappe.db.get_single_value("HR Settings", "email_group")
		if not email_group:
			frappe.throw("HR Users Email Group not set in HR Settings.")
		hr_users = frappe.get_list(
			"Email Group Member", filters={"email_group": email_group}, fields=["email"]
		)
		if hr_users:
			receipients = [a["email"] for a in hr_users]
			parent_doc = frappe.get_doc(self.doc.doctype, self.doc.name)
			args = parent_doc.as_dict()

			if self.doc.doctype == "Leave Application":
				template = frappe.db.get_single_value(
					"HR Settings", "leave_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Leave Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Leave Encashment":
				template = frappe.db.get_single_value(
					"HR Settings", "encashment_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Encashment Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Salary Advance":
				template = frappe.db.get_single_value(
					"HR Settings", "advance_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Advance Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Overtime Application":
				template = frappe.db.get_single_value(
					"HR Settings", "overtime_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Overtime Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Employee Benefits":
				template = frappe.db.get_single_value(
					"HR Settings", "benefits_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Employee Benefits Approval Notification in HR Settings."
						)
					)
					return
			elif self.doc.doctype == "Employee Separation":
				template = frappe.db.get_single_value(
					"HR Settings", "employee_separation_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Employee Separation Approval Notification in HR Settings."
						)
					)
					return
			else:
				template = ""

			if not template:
				frappe.msgprint(
					_("Please set default template for {}.").format(self.doc.doctype)
				)
				return
			email_template = frappe.get_doc("Email Template", template)
			message = frappe.render_template(email_template.response, args)
			# frappe.throw(self.doc.get(self.doc_approver[0]))
			self.notify(
				{
					# for post in messages
					"message": message,
					"message_to": receipients,
					# for email
					"subject": email_template.subject,
				}
			)

	def notify_ta_finance(self):
		receipients = []
		region = frappe.db.get_value("Employee", self.doc.employee, "region")
		email_group = "Travel Administrator, Finance"
		ta = frappe.get_list(
			"Email Group Member", filters={"email_group": email_group}, fields=["email"]
		)
		if ta:
			receipients = [a["email"] for a in ta]
			parent_doc = frappe.get_doc(self.doc.doctype, self.doc.name)
			args = parent_doc.as_dict()
			if self.doc.doctype == "Travel Claim":
				template = frappe.db.get_single_value(
					"HR Settings", "claim_approval_notification_template"
				)
				if not template:
					frappe.msgprint(
						_(
							"Please set default template for Claim Approval Notification in HR Settings."
						)
					)
					return
			if not template:
				frappe.msgprint(
					_("Please set default template for {}.").format(self.doc.doctype)
				)
				return
			email_template = frappe.get_doc("Email Template", template)
			message = frappe.render_template(email_template.response, args)
			# frappe.throw(self.doc.get(self.doc_approver[0]))
			self.notify(
				{
					# for post in messages
					"message": message,
					"message_to": receipients,
					# for email
					"subject": email_template.subject,
				}
			)
	def notify_user_role(self,wf_state):
		"""
		Notify users based on Travel Claim workflow state.
		Sends email to the role responsible for current workflow state.
		"""
		try:
			recipients = []
			

			# wf_state = self.doc.workflow_state

			# Map workflow state to role
			role_map = {
				"Waiting for Verification": "HR User",
				"Waiting for Finance Verification": "Accounts User",
				"Waiting Recommendation": "Accounts Manager",
				"Waiting Approval": "Approver"
			}

			role = role_map.get(wf_state)

			# Get emails for the role
			if role:
				users_with_role = frappe.get_all("Has Role", filters={"role": role}, pluck="parent")
			

				for user in users_with_role:
					email = frappe.db.get_value("User", user, "email")
					if email:
						recipients.append(email)
			else:
				# Final states: notify employee
				if self.doc.employee:
					email = frappe.db.get_value("Employee", self.doc.employee, "user_id")
					if email:
						recipients.append(email)

			if not recipients:
				frappe.msgprint(_("No valid recipients found for workflow state: {0}").format(wf_state))
				return

			# Get template
			template_name = frappe.db.get_single_value(
				"HR Settings", "travel_claim_approval_notification_template"
			)
			if not template_name:
				frappe.msgprint(_("Please set default template for Claim Approval Notification in HR Settings."))
				return

			email_template = frappe.get_doc("Email Template", template_name)

			# Render message
			args = self.doc.as_dict()
			message = frappe.render_template(email_template.response, args)

			# Send notification
		
			self.notify({
				"message": message,
				"message_to":recipients,
				"subject": email_template.subject,
			})

			frappe.msgprint(_("Notification sent successfully to: {0}").format(", ".join(recipients)))

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "TravelClaim.notify_user_role Error")
			frappe.throw(_("Notification sending failed: {0}").format(str(e)))



	def notify(self, args):
		args = frappe._dict(args)
		# args -> message, message_to, subject
		contact = args.message_to
		if not isinstance(contact, list):
			if not args.notify == "employee":
				contact = frappe.get_doc("User", contact).email or contact

		sender = dict()
		sender["email"] = frappe.get_doc("User", frappe.session.user).email
		sender["full_name"] = frappe.utils.get_fullname(sender["email"])

		try:
			frappe.sendmail(
				recipients=contact,
				sender=sender["email"],
				subject=args.subject,
				message=args.message,
			)
			frappe.msgprint(_("Email sent to {0}").format(contact))
		except frappe.OutgoingEmailError:
			pass

	def send_notification(self):
		if self.doc.doctype == "Travel Claim":
			wf_state = self.new_state  # use new_state, not workflow_state
			self.notify_user_role(wf_state)
			return
		if (self.doc.doctype not in self.field_map) or not frappe.db.exists(
			"Workflow", {"document_type": self.doc.doctype, "is_active": 1}
		):
			return

		if self.new_state == "Draft":
			return

		if self.doc.workflow_state == "Waiting for Verification":
			self.notify_verifier()
		elif self.new_state.lower() == "waiting approval":
			self.notify_approver()
		elif self.new_state in (
			"Approved",
			"Rejected",
			"Cancelled",
			"Claimed",
			"Submitted",
		):
			if (
				self.doc.doctype == "Material Request"
				and self.doc.owner != "Administrator"
			):
				self.notify_employee()
			else:
				self.notify_employee()
		elif (
			self.new_state.startswith("Waiting")
			and self.old_state != self.new_state
			and self.doc.doctype
			not in ("Asset Issue Details", "Project Capitalization")
		):
			self.notify_approver()

		else:
			frappe.msgprint(
				_("Email notifications not configured for workflow state {}").format(
					self.new_state
				)
			)


def get_field_map():
	return {
		"Leave Application": [
			"leave_approver",
			"leave_approver_name",
			"leave_approver_designation",
		],
		"Travel Request": ["supervisor", "supervisor_name", "supervisor_designation"],
		# ======= Added by Nyuethyue ======== #
		"Employee Advance": ["approver", "approver_name", "approver_designation"],
		"Leave Encashment": ["approver", "approver_name", "approver_designation"],
		"Travel Authorization": ["approver", "approver_name", "approver_designation"],
		"Travel Claim": ["approver", "approver_name", "approver_designation"],
		"Travel Advance": ["approver", "approver_name", "approver_designation"],
		"Travel Adjustment": ["approver", "approver_name", "approver_designation"],
		# ======= End Here ======== #
		"SWS Application": ["supervisor", "supervisor_name", "supervisor_designation"],
		"SWS Membership": ["supervisor", "supervisor_name", "supervisor_designation"],
		"Vehicle Request": ["approver_id", "approver"],
		"Repair And Services": ["approver", "approver_name", "aprover_designation"],
		"Overtime Application": [
			"ot_approver",
			"ot_approver_name",
			"approver_designation",
		],
		"POL Expense": ["approver", "approver_name", "approver_designation"],
		"Material Request": ["approver", "approver_name", "approver_designation"],
		"Asset Movement": ["approver", "approver_name", "approver_designation"],
		"Budget Reappropiation": ["approver", "approver_name", "approver_designation"],
		"Employee Transfer": [
			"supervisor",
			"supervisor_name",
			"supervisor_designation",
		],
		"Employee Benefits": [
			"benefit_approver",
			"benefit_approver_name",
			"benefit_approver_designation",
		],
		"Compile Budget": ["approver", "approver_name"],
		"Target Set Up": ["approver", "approver_name", "approver_designation"],
		"Review": ["approver", "approver_name", "approver_designation"],
		"Performance Evaluation": ["approver", "approver_name", "approver_designation"],
		"Employee Separation": ["approver", "approver_name", "approver_designation"],
		"POL": ["approver", "approver_name", "approver_designation"],
		"Contract Renewal Application": [
			"approver",
			"approver_name",
			"approver_designation",
		],
		"Promotion Application": ["approver", "approver_name", "approver_designation"],
		"PMS Appeal": ["approver", "approver_name", "approver_designation"],
		"Asset Issue Details": [],
	}


def validate_workflow_states(doc):
	wf = CustomWorkflow(doc)
	wf.apply_workflow()


def notify_workflow_states(doc):
	wf = NotifyCustomWorkflow(doc)
	wf.send_notification()
