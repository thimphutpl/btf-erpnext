frappe.query_reports["Project report"] = {
    filters: [
        {
            fieldname: "funding_source",
            label: __("Funding Source"),
            fieldtype: "Data"
        },
        {
            fieldname: "thematic",
            label: __("Thematic"),
            fieldtype: "Data"
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },
        {
            fieldname: "project_title",
            label: __("Project Title Contains"),
            fieldtype: "Data"
        }
    ]
};