from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeClassification:
    label: str
    reason_codes: tuple[str, ...]
    threshold_values: dict[str, float]
    confidence: float


SUPPORTED_REGIME_LABELS = (
    "coherent-dominated",
    "dephasing-assisted",
    "localized-by-disorder",
    "loss-dominated",
    "strongly-damped",
    "mixed-crossover",
)


def _clip_confidence(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def classify_regime(
    *,
    transport_efficiency: float,
    coherent_efficiency_reference: float,
    best_efficiency_reference: float,
    final_loss_population: float,
    disorder_strength_over_coupling: float,
    dephasing_over_coupling: float,
    mean_coherence_l1: float,
    final_participation_ratio: float,
    final_entropy: float,
    final_mean_squared_displacement: float,
    max_mean_squared_displacement_reference: float,
    n_sites: int,
) -> RegimeClassification:
    thresholds = {
        "loss_dominated_population": 0.35,
        "assistant_gain_absolute": 0.03,
        "assistant_gain_relative": 0.05,
        "localized_disorder_ratio": 0.50,
        "localized_participation_fraction": 0.45,
        "localized_msd_fraction": 0.45,
        "strong_damping_ratio": 0.60,
        "strong_damping_msd_fraction": 0.55,
        "coherent_small_dephasing": 0.05,
    }

    reason_codes: list[str] = []
    max_msd_reference = max(float(max_mean_squared_displacement_reference), 1e-12)
    participation_fraction = float(final_participation_ratio) / max(float(n_sites), 1.0)
    msd_fraction = float(final_mean_squared_displacement) / max_msd_reference
    gain_absolute = float(transport_efficiency - coherent_efficiency_reference)
    gain_relative = gain_absolute / max(abs(float(coherent_efficiency_reference)), 1e-12)

    if final_loss_population >= thresholds["loss_dominated_population"] and final_loss_population > transport_efficiency:
        reason_codes.extend(("loss_high", "loss_exceeds_success"))
        confidence = _clip_confidence(
            0.55
            + 0.75 * (final_loss_population - thresholds["loss_dominated_population"])
            + 0.35 * max(final_loss_population - transport_efficiency, 0.0)
        )
        return RegimeClassification(
            label="loss-dominated",
            reason_codes=tuple(reason_codes),
            threshold_values=thresholds,
            confidence=confidence,
        )

    if (
        disorder_strength_over_coupling >= thresholds["localized_disorder_ratio"]
        and participation_fraction <= thresholds["localized_participation_fraction"]
        and msd_fraction <= thresholds["localized_msd_fraction"]
        and transport_efficiency <= 0.85 * max(best_efficiency_reference, 1e-12)
    ):
        reason_codes.extend(("disorder_high", "spreading_low", "participation_low"))
        confidence = _clip_confidence(
            0.50
            + 0.45 * (disorder_strength_over_coupling - thresholds["localized_disorder_ratio"])
            + 0.25 * (thresholds["localized_participation_fraction"] - participation_fraction)
            + 0.25 * (thresholds["localized_msd_fraction"] - msd_fraction)
        )
        return RegimeClassification(
            label="localized-by-disorder",
            reason_codes=tuple(reason_codes),
            threshold_values=thresholds,
            confidence=confidence,
        )

    if (
        dephasing_over_coupling >= thresholds["strong_damping_ratio"]
        and msd_fraction <= thresholds["strong_damping_msd_fraction"]
        and transport_efficiency <= 0.90 * max(best_efficiency_reference, 1e-12)
    ):
        reason_codes.extend(("dephasing_high", "spreading_suppressed"))
        confidence = _clip_confidence(
            0.45
            + 0.45 * (dephasing_over_coupling - thresholds["strong_damping_ratio"])
            + 0.25 * (thresholds["strong_damping_msd_fraction"] - msd_fraction)
        )
        return RegimeClassification(
            label="strongly-damped",
            reason_codes=tuple(reason_codes),
            threshold_values=thresholds,
            confidence=confidence,
        )

    if (
        gain_absolute >= thresholds["assistant_gain_absolute"]
        and gain_relative >= thresholds["assistant_gain_relative"]
        and dephasing_over_coupling > thresholds["coherent_small_dephasing"]
        and final_loss_population < thresholds["loss_dominated_population"]
    ):
        reason_codes.extend(("success_improves_with_scrambling", "nonzero_dephasing_optimum"))
        confidence = _clip_confidence(
            0.45
            + 0.70 * (gain_absolute - thresholds["assistant_gain_absolute"])
            + 0.35 * (gain_relative - thresholds["assistant_gain_relative"])
        )
        return RegimeClassification(
            label="dephasing-assisted",
            reason_codes=tuple(reason_codes),
            threshold_values=thresholds,
            confidence=confidence,
        )

    if (
        dephasing_over_coupling <= thresholds["coherent_small_dephasing"]
        and transport_efficiency >= 0.97 * max(coherent_efficiency_reference, 1e-12)
        and mean_coherence_l1 >= 0.10
    ):
        reason_codes.extend(("best_point_near_zero_scrambling", "coherence_retained"))
        confidence = _clip_confidence(
            0.45
            + 0.40 * (thresholds["coherent_small_dephasing"] - dephasing_over_coupling)
            + 0.20 * min(mean_coherence_l1, 1.0)
        )
        return RegimeClassification(
            label="coherent-dominated",
            reason_codes=tuple(reason_codes),
            threshold_values=thresholds,
            confidence=confidence,
        )

    reason_codes.extend(("boundary_case", "thresholds_compete"))
    confidence = _clip_confidence(
        0.30
        + 0.10 * abs(gain_absolute)
        + 0.05 * abs(gain_relative)
        + 0.05 * final_entropy
    )
    return RegimeClassification(
        label="mixed-crossover",
        reason_codes=tuple(reason_codes),
        threshold_values=thresholds,
        confidence=confidence,
    )
