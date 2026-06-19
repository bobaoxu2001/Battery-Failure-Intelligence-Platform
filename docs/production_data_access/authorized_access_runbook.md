# Authorized Access Runbook

This runbook describes how the project would connect to production battery data only after formal authorization. It is not a guide to bypass access controls.

## 1. Confirm Authorization

1. Identify the data owner for each source table or API.
2. Document the allowed use case, scope, retention period, and approved output types.
3. Confirm whether data can be copied locally, aggregated only, or queried in place.
4. Confirm privacy, confidentiality, export-control, and incident-response requirements.

## 2. Provision Least-Privilege Access

1. Use read-only credentials scoped to the minimum tables, columns, rows, and time windows needed.
2. Prefer approved identity, VPN, warehouse, API gateway, or service-account flows.
3. Store secrets in an approved secret manager or environment variables.
4. Never commit credentials, `.env`, tokens, raw exports, or private endpoint details.

## 3. Configure The Connector

1. Copy `.env.example` to a local untracked `.env` or load variables through the approved runtime.
2. Set `BFI_PROD_DB_URI`, `BFI_PROD_DB_SCHEMA`, `BFI_PROD_READ_ONLY=true`, and `BFI_PROD_SAMPLE_LIMIT`.
3. Run `python -m src.ingest.production_connector --dry-run` to validate configuration without connecting.
4. Run `python -m src.ingest.production_connector --schema-contract-only` to review required tables and columns.

## 4. Validate Schema And Data Quality

1. Compare available tables/columns against `production_data_contract.md`.
2. Validate primary keys, timestamp fields, measurement ranges, and null constraints.
3. Check that labels are available only at the correct time and do not leak future outcomes into training features.
4. Reconcile row counts by lot, station, protocol, time window, and cell group with source-system owners.

## 5. Run Approved Derivations Only

1. Pull only approved rows and columns.
2. Prefer aggregate or feature-level outputs over raw records.
3. Write only derived summaries, approved samples, and reports to local storage.
4. Keep raw production data in governed systems unless explicit approval allows local copies.

## 6. Document Lineage And Retention

1. Record source system, schema version, query window, approval ticket, and run timestamp.
2. Store model version, feature snapshot ID, and report lineage with every output.
3. Apply approved retention and deletion rules.
4. Revalidate access if the use case, audience, model, or output type changes.

## 7. Stop Conditions

Stop and ask the data owner/security team before proceeding if:

- Credentials are missing, shared informally, over-permissioned, or stored in files.
- Data appears to include fields outside the approved scope.
- Raw exports would land in Git, email, chat, or unmanaged storage.
- A label or feature might expose confidential engineering decisions beyond the approved use case.
