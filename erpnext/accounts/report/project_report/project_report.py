# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})

    project_fields = get_project_field_config()

    columns = get_columns(project_fields)
    data = get_data(filters, project_fields)

    return columns, data


def get_columns(project_fields):
    return [
        {
            "label": _("Funding Source ID"),
            "fieldname": "funding_source_id",
            "fieldtype": get_column_fieldtype(
                project_fields.get("funding_source_id")
            ),
            "options": get_link_options(
                project_fields.get("funding_source_id")
            ),
            "width": 160,
        },
        {
            "label": _("Funding Source Title"),
            "fieldname": "funding_source_title",
            "fieldtype": "Data",
            "width": 280,
        },
        {
            "label": _("Thematic ID"),
            "fieldname": "thematic_id",
            "fieldtype": get_column_fieldtype(
                project_fields.get("thematic_id")
            ),
            "options": get_link_options(
                project_fields.get("thematic_id")
            ),
            "width": 160,
        },
        {
            "label": _("Thematic Title"),
            "fieldname": "thematic_title",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": _("Project ID"),
            "fieldname": "project_id",
            "fieldtype": "Link",
            "options": "Project",
            "width": 160,
        },
        {
            "label": _("Project Title"),
            "fieldname": "project_title",
            "fieldtype": "Data",
            "width": 300,
        },
    ]


def get_project_field_config():
    """
    Find the Funding Source and Thematic fields inside Project.

    This avoids using nonexistent tables such as:
        tabFunding Source
        tabThematic
    """

    meta = frappe.get_meta("Project")

    return frappe._dict(
        {
            "funding_source_id": find_project_field(
                meta=meta,
                possible_fieldnames=[
                    "funding_source",
                    "custom_funding_source",
                    "funding_source_id",
                    "custom_funding_source_id",
                    "source_of_funding",
                    "custom_source_of_funding",
                ],
                required_words=["fund"],
                excluded_words=["title", "name"],
            ),
            "funding_source_title": find_project_field(
                meta=meta,
                possible_fieldnames=[
                    "funding_source_title",
                    "custom_funding_source_title",
                    "funding_source_name",
                    "custom_funding_source_name",
                ],
                required_words=["fund"],
                included_title_words=["title", "name"],
            ),
            "thematic_id": find_project_field(
                meta=meta,
                possible_fieldnames=[
                    "thematic",
                    "custom_thematic",
                    "thematic_id",
                    "custom_thematic_id",
                    "thematic_area",
                    "custom_thematic_area",
                ],
                required_words=["thematic"],
                excluded_words=["title", "name"],
            ),
            "thematic_title": find_project_field(
                meta=meta,
                possible_fieldnames=[
                    "thematic_title",
                    "custom_thematic_title",
                    "thematic_name",
                    "custom_thematic_name",
                ],
                required_words=["thematic"],
                included_title_words=["title", "name"],
            ),
        }
    )


def find_project_field(
    meta,
    possible_fieldnames,
    required_words,
    excluded_words=None,
    included_title_words=None,
):
    excluded_words = excluded_words or []
    included_title_words = included_title_words or []

    allowed_fieldtypes = {
        "Data",
        "Link",
        "Dynamic Link",
        "Select",
        "Read Only",
        "Small Text",
        "Text",
    }

    fields_by_name = {
        field.fieldname: field
        for field in meta.fields
        if field.fieldname
    }

    # First check common fieldnames
    for fieldname in possible_fieldnames:
        field = fields_by_name.get(fieldname)

        if field and field.fieldtype in allowed_fieldtypes:
            return field

    # Otherwise check label and fieldname text
    matches = []

    for field in meta.fields:
        if not field.fieldname:
            continue

        if field.fieldtype not in allowed_fieldtypes:
            continue

        search_text = (
            f"{field.label or ''} {field.fieldname or ''}"
            .replace("_", " ")
            .lower()
        )

        if not all(
            word.lower() in search_text
            for word in required_words
        ):
            continue

        if any(
            word.lower() in search_text
            for word in excluded_words
        ):
            continue

        if included_title_words:
            if not any(
                word.lower() in search_text
                for word in included_title_words
            ):
                continue

        matches.append(field)

    if not matches:
        return None

    # Prefer Link fields, then custom fields
    matches.sort(
        key=lambda field: (
            0 if field.fieldtype == "Link" else 1,
            0 if field.fieldname.startswith("custom_") else 1,
        )
    )

    return matches[0]


def get_data(filters, project_fields):
    database_filters = {
        "docstatus": ["<", 2]
    }

    funding_source_field = project_fields.get(
        "funding_source_id"
    )

    thematic_field = project_fields.get("thematic_id")

    if filters.get("funding_source") and funding_source_field:
        database_filters[funding_source_field.fieldname] = (
            filters.get("funding_source")
        )

    if filters.get("thematic") and thematic_field:
        database_filters[thematic_field.fieldname] = (
            filters.get("thematic")
        )

    if filters.get("project"):
        database_filters["name"] = filters.get("project")

    if filters.get("project_title"):
        database_filters["project_name"] = [
            "like",
            f"%{filters.get('project_title')}%",
        ]

    fields = [
        "name",
        "project_name",
    ]

    add_field(
        fields,
        project_fields.get("funding_source_id"),
    )

    add_field(
        fields,
        project_fields.get("funding_source_title"),
    )

    add_field(
        fields,
        project_fields.get("thematic_id"),
    )

    add_field(
        fields,
        project_fields.get("thematic_title"),
    )

    projects = frappe.get_all(
        "Project",
        filters=database_filters,
        fields=fields,
        order_by="name asc",
    )

    funding_source_title_map = get_link_title_map(
        projects,
        project_fields.get("funding_source_id"),
    )

    thematic_title_map = get_link_title_map(
        projects,
        project_fields.get("thematic_id"),
    )

    data = []

    for project in projects:
        funding_source_id = get_value(
            project,
            project_fields.get("funding_source_id"),
        )

        thematic_id = get_value(
            project,
            project_fields.get("thematic_id"),
        )

        funding_source_title = get_title(
            record=project,
            direct_title_field=project_fields.get(
                "funding_source_title"
            ),
            link_value=funding_source_id,
            title_map=funding_source_title_map,
        )

        thematic_title = get_title(
            record=project,
            direct_title_field=project_fields.get(
                "thematic_title"
            ),
            link_value=thematic_id,
            title_map=thematic_title_map,
        )

        data.append(
            {
                "funding_source_id": funding_source_id,
                "funding_source_title": funding_source_title,
                "thematic_id": thematic_id,
                "thematic_title": thematic_title,
                "project_id": project.name,
                "project_title": (
                    project.project_name or project.name
                ),
            }
        )

    return data


def add_field(fields, field):
    if not field:
        return

    if field.fieldname not in fields:
        fields.append(field.fieldname)


def get_value(record, field):
    if not field:
        return ""

    return record.get(field.fieldname) or ""


def get_title(
    record,
    direct_title_field,
    link_value,
    title_map,
):
    if direct_title_field:
        direct_title = record.get(
            direct_title_field.fieldname
        )

        if direct_title:
            return direct_title

    if link_value:
        return title_map.get(link_value) or link_value

    return ""


def get_link_title_map(records, link_field):
    if not link_field:
        return {}

    if link_field.fieldtype != "Link":
        return {}

    linked_doctype = link_field.options

    if not linked_doctype:
        return {}

    if not frappe.db.exists("DocType", linked_doctype):
        return {}

    linked_names = list(
        {
            record.get(link_field.fieldname)
            for record in records
            if record.get(link_field.fieldname)
        }
    )

    if not linked_names:
        return {}

    linked_meta = frappe.get_meta(linked_doctype)
    title_field = get_title_field(linked_meta)

    if not title_field:
        return {
            name: name
            for name in linked_names
        }

    linked_records = frappe.get_all(
        linked_doctype,
        filters={
            "name": ["in", linked_names]
        },
        fields=[
            "name",
            title_field,
        ],
    )

    return {
        record.name: (
            record.get(title_field) or record.name
        )
        for record in linked_records
    }


def get_title_field(meta):
    if meta.title_field:
        if meta.get_field(meta.title_field):
            return meta.title_field

    possible_fields = [
        "funding_source_title",
        "thematic_title",
        "project_name",
        "source_title",
        "title",
        "name1",
        "description",
    ]

    for fieldname in possible_fields:
        if meta.get_field(fieldname):
            return fieldname

    return None


def get_column_fieldtype(field):
    if field and field.fieldtype == "Link":
        return "Link"

    return "Data"


def get_link_options(field):
    if not field:
        return None

    if field.fieldtype != "Link":
        return None

    if not field.options:
        return None

    if not frappe.db.exists("DocType", field.options):
        return None

    return field.options