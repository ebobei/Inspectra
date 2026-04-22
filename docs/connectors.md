# Connectors

Inspectra currently supports three external systems:
- Jira
- GitLab
- Confluence

Inspectra does not expose a generic connector SDK in this version. These adapters are intentionally simple and tied to the product use-case.

## Jira
- source type: `jira_issue`
- external id format: `PROJ-123`
- supports fetch + create/update comment
- this is the primary and most production-like path in the current repository

## GitLab
- source type: `gitlab_merge_request`
- external id format: `project_id!mr_iid` or `group%2Fproject!mr_iid`
- supports fetch + create/update merge request note
- treat this as supported, but still validate against your GitLab version and permissions model

## Confluence
- source type: `confluence_page`
- external id format: `page_id`
- supports fetch + create/update page footer comment
- treat this as implemented but higher-risk than Jira; validate against your exact Confluence deployment before broader rollout
