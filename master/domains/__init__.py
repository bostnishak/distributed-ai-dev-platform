"""Strict Domain Engines & Zero-Code YAML Domain Framework (`master/domains/`): DOM-01..DOM-12."""

from domains.api import router
from domains.engines import (
    DimensionalityError,
    MissingDomainInputsError,
    UnitQuantity,
    analyze_legal_contract,
    compute_kienzle_cutting_force,
    evaluate_cnc_ballooning_accuracy,
    evaluate_health_query,
    generate_verified_math_exercise,
    run_finance_dcf,
    solve_polynomial_derivative_crosschecked,
    validate_gcode_safety,
    verify_tutor_code_output,
)
from domains.registry import SPECS_DIR, load_all_domain_specs, validate_domain_spec

__all__ = [
    "SPECS_DIR",
    "DimensionalityError",
    "MissingDomainInputsError",
    "UnitQuantity",
    "analyze_legal_contract",
    "compute_kienzle_cutting_force",
    "evaluate_cnc_ballooning_accuracy",
    "evaluate_health_query",
    "generate_verified_math_exercise",
    "load_all_domain_specs",
    "router",
    "run_finance_dcf",
    "solve_polynomial_derivative_crosschecked",
    "validate_domain_spec",
    "validate_gcode_safety",
    "verify_tutor_code_output",
]
