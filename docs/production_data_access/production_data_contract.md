# Production Data Contract

This contract describes the authorized production tables or streams this project would need in a real battery engineering environment. It is a schema contract only. It does not grant access to any system and does not include proprietary data.

## General Rules

- Access must be approved by the data owner and limited to the authorized interview/work use case.
- Credentials must come from environment variables or an approved secret manager, never from committed files.
- Raw production records should remain in approved systems; local outputs should be derived aggregates, validation summaries, or approved samples only.
- Data types below are examples and should be reconciled with the actual warehouse/API schema before use.

## Table Contracts

### factory_cell_tests

- Grain: one row per cell acceptance test.
- Primary key: `cell_test_id`.
- Important columns: `cell_id`, `lot_id`, `batch_id`, `station_id`, `fixture_id`, `equipment_id`, `test_protocol`, `test_temperature_c`, `charge_current_a`, `discharge_current_a`, `initial_capacity_ah`, `initial_resistance_mohm`, `pass_fail_flag`.
- Timestamp fields: `manufacturing_ts`, `test_start_ts`, `test_end_ts`, `ingested_at`.
- Example data types: strings for IDs/protocols, decimals for measurements, booleans for flags, UTC timestamps.
- Data-quality checks: unique `cell_test_id`; non-null `cell_id`, `lot_id`, `station_id`; positive capacity/resistance/current; valid temperature range; `test_end_ts >= test_start_ts`; no duplicate active test for the same cell/protocol.
- Privacy/confidentiality notes: may reveal process routes, station identity, lot genealogy, and manufacturing timing; treat as confidential.
- Current warehouse mapping: maps to `dim_cell`, `dim_lot`, `dim_station`, `dim_test_condition`, and factory fields in the synthetic `factory.csv`.

### cycle_measurements

- Grain: one row per cell per cycle or summarized cycle segment.
- Primary key: `cell_id`, `cycle_index`, `measurement_protocol`.
- Important columns: `cell_id`, `cycle_index`, `voltage_mean_v`, `voltage_min_v`, `voltage_max_v`, `current_mean_a`, `temperature_mean_c`, `temperature_max_c`, `discharge_capacity_ah`, `charge_capacity_ah`, `energy_wh`, `internal_resistance_mohm`, `cycler_channel_id`.
- Timestamp fields: `cycle_start_ts`, `cycle_end_ts`, `ingested_at`.
- Example data types: integer cycle index, decimals for measurements, strings for protocol/channel, UTC timestamps.
- Data-quality checks: unique cell-cycle grain; positive capacity and resistance; plausible voltage/current/temperature ranges; monotonic cycle order per cell; no unexplained cycle gaps.
- Privacy/confidentiality notes: can reveal test protocols, cell behavior, and lab equipment identity.
- Current warehouse mapping: maps to `fact_cycle_measurements` and cycle-level feature engineering.

### impedance_measurements

- Grain: one row per cell per impedance test frequency or summarized impedance test.
- Primary key: `impedance_measurement_id`.
- Important columns: `cell_id`, `cycle_index`, `frequency_hz`, `re_ohm`, `rct_ohm`, `impedance_magnitude_ohm`, `impedance_phase_deg`, `test_protocol`, `station_id`.
- Timestamp fields: `measurement_ts`, `ingested_at`.
- Example data types: decimals for impedance/frequency, strings for IDs/protocols, UTC timestamps.
- Data-quality checks: positive frequency; non-negative impedance components; valid cell references; protocol-specific expected frequency coverage.
- Privacy/confidentiality notes: can reveal detailed electrochemical diagnostics and internal test settings.
- Current warehouse mapping: no direct fact table yet; candidate extension to feature engineering and cell-health marts.

### usage_telemetry

- Grain: one row per cell/device/day or per summarized usage window.
- Primary key: `usage_window_id`.
- Important columns: `cell_id`, `device_id_hash`, `window_start_ts`, `window_end_ts`, `avg_depth_of_discharge`, `fast_charge_ratio`, `avg_daily_cycles`, `high_temp_exposure_hours`, `low_temp_exposure_hours`, `usage_profile`.
- Timestamp fields: `window_start_ts`, `window_end_ts`, `ingested_at`.
- Example data types: hashed identifiers, decimals for aggregates, strings for profile labels, UTC timestamps.
- Data-quality checks: `window_end_ts > window_start_ts`; bounded ratios between 0 and 1; non-negative exposure hours; no raw personally identifying fields.
- Privacy/confidentiality notes: usage telemetry may be sensitive even when aggregated; use only approved, privacy-reviewed fields.
- Current warehouse mapping: maps to `fact_usage_profile` and synthetic `usage.csv`.

### failure_events

- Grain: one row per cell event or engineer-reviewed failure label.
- Primary key: `failure_event_id`.
- Important columns: `cell_id`, `event_type`, `failure_mode`, `capacity_drop_event`, `impedance_spike_event`, `thermal_anomaly_event`, `early_degradation_flag`, `escalation_required`, `failure_severity`, `label_source`, `reviewer_role`.
- Timestamp fields: `event_ts`, `label_reviewed_ts`, `ingested_at`.
- Example data types: strings/enums for event fields, booleans for flags, UTC timestamps.
- Data-quality checks: valid event type/severity; label source present; reviewed labels separated from model predictions; no target leakage into pre-event features.
- Privacy/confidentiality notes: may reveal reliability issues and engineering decisions; treat as highly confidential.
- Current warehouse mapping: maps to `fact_failure_events` and model training labels.

### quality_holds

- Grain: one row per hold action on a lot, batch, station, or cell group.
- Primary key: `quality_hold_id`.
- Important columns: `hold_scope`, `lot_id`, `batch_id`, `station_id`, `cell_id`, `hold_reason`, `hold_status`, `opened_by_role`, `released_by_role`, `release_criteria`.
- Timestamp fields: `hold_opened_ts`, `hold_closed_ts`, `ingested_at`.
- Example data types: strings/enums for scope/status/reason, UTC timestamps.
- Data-quality checks: valid status transitions; closed holds require close timestamp and release criteria; scoped IDs must match scope.
- Privacy/confidentiality notes: may expose manufacturing quality decisions and internal escalation history.
- Current warehouse mapping: candidate extension to `mart_factory_quality` and escalation reporting.

### engineering_dispositions

- Grain: one row per engineer disposition or follow-up action.
- Primary key: `disposition_id`.
- Important columns: `cell_id`, `quality_hold_id`, `failure_event_id`, `disposition_code`, `root_cause_category`, `recommended_action`, `action_owner_role`, `teardown_required`, `retest_required`, `final_outcome`.
- Timestamp fields: `disposition_ts`, `action_due_ts`, `closed_ts`, `ingested_at`.
- Example data types: strings/enums for decisions, booleans for actions, UTC timestamps.
- Data-quality checks: disposition must reference an event/hold/cell; final outcome required for closed dispositions; no future closed timestamps.
- Privacy/confidentiality notes: may reveal internal root-cause analysis and decision processes.
- Current warehouse mapping: maps to escalation report follow-up fields and can calibrate false positives/negatives.

### station_calibration_logs

- Grain: one row per station calibration event.
- Primary key: `calibration_event_id`.
- Important columns: `station_id`, `equipment_id`, `fixture_id`, `calibration_status`, `calibration_type`, `measurement_drift_pct`, `technician_role`, `maintenance_ticket_id`.
- Timestamp fields: `calibration_ts`, `valid_from_ts`, `valid_to_ts`, `ingested_at`.
- Example data types: strings/enums for status/type, decimals for drift, UTC timestamps.
- Data-quality checks: non-null station/equipment IDs; drift within expected bounds; calibration validity windows do not overlap unexpectedly.
- Privacy/confidentiality notes: can expose station maintenance and process-control history.
- Current warehouse mapping: enriches `dim_station`, `mart_factory_quality`, and station anomaly features.

### model_predictions

- Grain: one row per model run per cell.
- Primary key: `prediction_id`.
- Important columns: `cell_id`, `model_name`, `model_version`, `predicted_soh`, `predicted_remaining_cycles`, `failure_probability`, `risk_tier`, `top_risk_driver`, `feature_snapshot_id`.
- Timestamp fields: `prediction_ts`, `feature_snapshot_ts`, `ingested_at`.
- Example data types: strings for model IDs, decimals for scores, UTC timestamps.
- Data-quality checks: one active prediction per cell/model/version; score ranges valid; model version present; feature snapshot lineage present.
- Privacy/confidentiality notes: predictions may drive production actions and should be access-controlled.
- Current warehouse mapping: maps to `fact_model_predictions`.

### escalation_actions

- Grain: one row per escalation action or review step.
- Primary key: `escalation_action_id`.
- Important columns: `cell_id`, `prediction_id`, `failure_event_id`, `action_type`, `action_status`, `review_decision`, `false_positive_flag`, `false_negative_flag`, `owner_role`, `notes_redacted`.
- Timestamp fields: `opened_ts`, `reviewed_ts`, `closed_ts`, `ingested_at`.
- Example data types: strings/enums for action fields, booleans for review labels, UTC timestamps.
- Data-quality checks: opened actions require owner/status; closed actions require review decision; false positive/negative flags require reviewed evidence.
- Privacy/confidentiality notes: must not store sensitive reviewer notes or unrestricted production details locally.
- Current warehouse mapping: candidate extension to escalation reporting, threshold calibration, and model monitoring.
