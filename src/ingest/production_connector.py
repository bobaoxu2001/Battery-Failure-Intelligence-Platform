"""Authorized-only production data connector scaffold.

This module intentionally does not connect to any private system by default.
It defines configuration, schema contracts, and safe CLI checks for a future
authorized environment. No proprietary production data is accessed.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


EXPECTED_SCHEMA: dict[str, list[str]] = {
    "factory_cell_tests": [
        "cell_test_id",
        "cell_id",
        "lot_id",
        "batch_id",
        "station_id",
        "fixture_id",
        "equipment_id",
        "test_protocol",
        "test_temperature_c",
        "charge_current_a",
        "discharge_current_a",
        "initial_capacity_ah",
        "initial_resistance_mohm",
        "pass_fail_flag",
        "manufacturing_ts",
        "test_start_ts",
        "test_end_ts",
    ],
    "cycle_measurements": [
        "cell_id",
        "cycle_index",
        "measurement_protocol",
        "cycle_start_ts",
        "cycle_end_ts",
        "voltage_mean_v",
        "voltage_min_v",
        "voltage_max_v",
        "current_mean_a",
        "temperature_mean_c",
        "temperature_max_c",
        "discharge_capacity_ah",
        "charge_capacity_ah",
        "energy_wh",
        "internal_resistance_mohm",
    ],
    "impedance_measurements": [
        "impedance_measurement_id",
        "cell_id",
        "cycle_index",
        "frequency_hz",
        "re_ohm",
        "rct_ohm",
        "impedance_magnitude_ohm",
        "impedance_phase_deg",
        "measurement_ts",
    ],
    "usage_telemetry": [
        "usage_window_id",
        "cell_id",
        "device_id_hash",
        "window_start_ts",
        "window_end_ts",
        "avg_depth_of_discharge",
        "fast_charge_ratio",
        "avg_daily_cycles",
        "high_temp_exposure_hours",
        "low_temp_exposure_hours",
        "usage_profile",
    ],
    "failure_events": [
        "failure_event_id",
        "cell_id",
        "event_ts",
        "event_type",
        "failure_mode",
        "capacity_drop_event",
        "impedance_spike_event",
        "thermal_anomaly_event",
        "early_degradation_flag",
        "escalation_required",
        "failure_severity",
        "label_source",
    ],
    "quality_holds": [
        "quality_hold_id",
        "hold_scope",
        "lot_id",
        "batch_id",
        "station_id",
        "cell_id",
        "hold_reason",
        "hold_status",
        "hold_opened_ts",
        "hold_closed_ts",
    ],
    "engineering_dispositions": [
        "disposition_id",
        "cell_id",
        "quality_hold_id",
        "failure_event_id",
        "disposition_code",
        "root_cause_category",
        "recommended_action",
        "teardown_required",
        "retest_required",
        "final_outcome",
        "disposition_ts",
    ],
    "station_calibration_logs": [
        "calibration_event_id",
        "station_id",
        "equipment_id",
        "fixture_id",
        "calibration_status",
        "calibration_type",
        "measurement_drift_pct",
        "calibration_ts",
        "valid_from_ts",
        "valid_to_ts",
    ],
    "model_predictions": [
        "prediction_id",
        "cell_id",
        "model_name",
        "model_version",
        "prediction_ts",
        "predicted_soh",
        "predicted_remaining_cycles",
        "failure_probability",
        "risk_tier",
        "top_risk_driver",
        "feature_snapshot_id",
    ],
    "escalation_actions": [
        "escalation_action_id",
        "cell_id",
        "prediction_id",
        "failure_event_id",
        "action_type",
        "action_status",
        "review_decision",
        "false_positive_flag",
        "false_negative_flag",
        "owner_role",
        "opened_ts",
        "reviewed_ts",
        "closed_ts",
    ],
}


class ProductionConnectorConfigError(RuntimeError):
    """Raised when authorized production connector settings are incomplete."""


@dataclass(frozen=True)
class ProductionDataConfig:
    """Environment-backed config for a future authorized production connector."""

    db_uri: str | None
    db_schema: str | None
    read_only: bool
    sample_limit: int

    @classmethod
    def from_env(cls, require_credentials: bool = True) -> "ProductionDataConfig":
        sample_limit_raw = os.getenv("BFI_PROD_SAMPLE_LIMIT", "10000")
        try:
            sample_limit = int(sample_limit_raw)
        except ValueError as exc:
            raise ProductionConnectorConfigError(
                "BFI_PROD_SAMPLE_LIMIT must be an integer."
            ) from exc
        if sample_limit <= 0:
            raise ProductionConnectorConfigError("BFI_PROD_SAMPLE_LIMIT must be positive.")

        read_only_raw = os.getenv("BFI_PROD_READ_ONLY", "true").strip().lower()
        if read_only_raw not in {"true", "1", "yes", "false", "0", "no"}:
            raise ProductionConnectorConfigError(
                "BFI_PROD_READ_ONLY must be true/false."
            )
        read_only = read_only_raw in {"true", "1", "yes"}
        cfg = cls(
            db_uri=os.getenv("BFI_PROD_DB_URI") or None,
            db_schema=os.getenv("BFI_PROD_DB_SCHEMA") or None,
            read_only=read_only,
            sample_limit=sample_limit,
        )
        if require_credentials:
            missing = []
            if not cfg.db_uri:
                missing.append("BFI_PROD_DB_URI")
            if not cfg.db_schema:
                missing.append("BFI_PROD_DB_SCHEMA")
            if missing:
                raise ProductionConnectorConfigError(
                    "Authorized production connector is not configured. Missing: "
                    + ", ".join(missing)
                    + ". Request approved read-only access and set environment variables; "
                    "do not commit credentials."
                )
            if not cfg.read_only:
                raise ProductionConnectorConfigError(
                    "BFI_PROD_READ_ONLY must remain true for this scaffold."
                )
        return cfg


def render_schema_contract() -> str:
    """Return a compact text version of expected production tables/columns."""
    lines = ["Expected authorized production schema:"]
    for table, columns in EXPECTED_SCHEMA.items():
        lines.append(f"- {table}: {', '.join(columns)}")
    return "\n".join(lines)


def _not_implemented(table_name: str, config: ProductionDataConfig | None = None) -> None:
    if config is None:
        ProductionDataConfig.from_env(require_credentials=True)
    raise NotImplementedError(
        f"{table_name} requires an explicitly implemented, authorized, read-only "
        "production connector. This scaffold never connects to private systems by default."
    )


def load_factory_cell_tests(config: ProductionDataConfig | None = None):
    _not_implemented("factory_cell_tests", config)


def load_cycle_measurements(config: ProductionDataConfig | None = None):
    _not_implemented("cycle_measurements", config)


def load_usage_telemetry(config: ProductionDataConfig | None = None):
    _not_implemented("usage_telemetry", config)


def load_failure_events(config: ProductionDataConfig | None = None):
    _not_implemented("failure_events", config)


def load_station_calibration_logs(config: ProductionDataConfig | None = None):
    _not_implemented("station_calibration_logs", config)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authorized-only production data connector scaffold."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate config without connecting")
    mode.add_argument(
        "--schema-contract-only",
        action="store_true",
        help="print expected production tables and columns without requiring credentials",
    )
    args = parser.parse_args()

    if args.schema_contract_only:
        print(render_schema_contract())
        return

    if args.dry_run:
        cfg = ProductionDataConfig.from_env(require_credentials=True)
        print("Production connector dry run passed.")
        print(f"Schema: {cfg.db_schema}")
        print(f"Read-only: {cfg.read_only}")
        print(f"Sample limit: {cfg.sample_limit}")
        print("No connection was opened and no production data was read.")


if __name__ == "__main__":
    main()
