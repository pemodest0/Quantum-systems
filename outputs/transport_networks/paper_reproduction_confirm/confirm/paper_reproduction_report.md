# Paper Reproduction And Validation Suite

Generated at UTC: 2026-04-22T00:40:33.899789+00:00
Profile: `confirm`

## Scope

This suite does not claim exact numerical reproduction of every paper. It tests whether the effective finite-network model reproduces the paper-level trend, control, or methodological claim that is relevant to this project.

## Overall Status

- Papers matched: 7.
- Papers diverged: 0.
- Papers inconclusive: 7.
- Papers not applicable: 3.
- Numerical validation passed: True.
- Open dynamic signatures evaluated: 1152.

## Paper-By-Paper Status

| Paper | Verdict | Claims | Mean confidence | Short reading |
|---|---:|---:|---:|---|
| `blach_2025` | `matched` | 2 | 0.90 | 1/1 central claims matched. |
| `caruso_2009` | `matched` | 1 | 1.00 | 1/1 central claims matched. |
| `coates_2023` | `inconclusive` | 1 | 0.35 | 0/1 central claims matched. |
| `engel_2007` | `not_applicable` | 1 | 1.00 | Outside model scope. |
| `gamble_2010` | `not_applicable` | 1 | 1.00 | Outside model scope. |
| `kendon_2007` | `matched` | 1 | 1.00 | 1/1 central claims matched. |
| `maier_2019` | `matched` | 2 | 0.90 | 1/1 central claims matched. |
| `minello_2019` | `inconclusive` | 1 | 0.50 | 0/1 central claims matched. |
| `mohseni_2008` | `matched` | 1 | 1.00 | 1/1 central claims matched. |
| `muelken_blumen_2011` | `inconclusive` | 1 | 0.70 | 0/1 central claims matched. |
| `novo_2016` | `inconclusive` | 1 | 0.80 | 0/1 central claims matched. |
| `plenio_huelga_2008` | `matched` | 1 | 1.00 | 1/1 central claims matched. |
| `razzoli_2021` | `inconclusive` | 2 | 0.38 | 0/2 central claims matched. |
| `rebentrost_2009` | `matched` | 1 | 0.85 | 1/1 central claims matched. |
| `rojo_francas_2024` | `not_applicable` | 1 | 1.00 | Outside model scope. |
| `rossi_2015` | `inconclusive` | 1 | 0.83 | 0/1 central claims matched. |
| `whitfield_2010` | `inconclusive` | 1 | 0.67 | 0/1 central claims matched. |

## Claim Details

| Paper | Claim | Expected trend | Observed metric | Threshold | Observed value | Verdict | Reason |
|---|---|---|---|---:|---:|---:|---|
| `muelken_blumen_2011` | `closed_ctqw_topology_dependence` | Closed CTQW observables depend on network topology. | `std(long_time_average_return)` | `0.01` | `0.0` | `inconclusive` | Closed-system topology separation is below threshold. |
| `razzoli_2021` | `trap_position_changes_efficiency` | Changing only trap/target position changes transport efficiency. | `max_target_position_spread` | `0.05` | `0.0` | `inconclusive` | Target placement effect is below threshold. |
| `razzoli_2021` | `connectivity_is_not_sufficient` | Target degree alone should not explain transport efficiency. | `r2(target_degree, target_arrival)` | `<0.75` | `1.0` | `inconclusive` | Degree correlation is too high or data are under-varied. |
| `plenio_huelga_2008` | `dephasing_assisted_transport` | Nonzero dephasing can improve useful target arrival. | `max_mean_dephasing_gain_with_ci95_low` | `0.05` | `0.17152676521947005` | `matched` | A nonzero dephasing point has gain above threshold with positive CI95 lower bound. |
| `mohseni_2008` | `enaqt_intermediate_regime` | Intermediate environment action improves sink efficiency, while strongest dephasing is not always optimal. | `dephasing_gain_and_high_dephasing_penalty` | `gain>=0.05 and penalty>0.02` | `gain=0.172; suppression=True` | `matched` | Best transport occurs at nonzero dephasing and high dephasing is not uniformly optimal. |
| `caruso_2009` | `noise_opens_transport_pathways_in_dissipative_networks` | Noise can improve excitation transfer through a dissipative network instead of only degrading it. | `positive_dephasing_gain_with_sink_loss_model` | `gain>=0.05 at nonzero dephasing` | `candidate_records=732; mean_loss=0.187` | `matched` | The sink/loss model contains cases where nonzero dephasing improves useful arrival. |
| `kendon_2007` | `decoherence_as_a_tunable_quantum_walk_parameter` | Moderate decoherence can tune quantum-walk spreading or mixing, while excessive decoherence removes coherent advantages. | `dephasing_gain_and_high_dephasing_penalty` | `gain>=0.05 and penalty>0.02` | `gain=0.172; suppression=True` | `matched` | The simulations show a useful nonzero-dephasing region and a high-dephasing penalty. |
| `rebentrost_2009` | `disorder_dephasing_efficiency_map` | Efficiency maps contain a useful intermediate dephasing window across disorder values. | `persistent_positive_dephasing_gain_and_high_noise_suppression` | `>=2 disorder values and penalty>0.02` | `persistent=True; suppression=True` | `matched` | Positive dephasing gain persists across disorder values and high-noise suppression appears. |
| `whitfield_2010` | `classical_quantum_walks_are_distinguishable_limits` | Quantum/open signatures should not be fully explained by the classical rate-walk control. | `max(quantum_only, quantum_minus_classical)-classical_only_accuracy` | `0.02` | `0.0` | `inconclusive` | Classical control explains most of the signal. |
| `rossi_2015` | `dynamic_signatures_encode_graph_similarity` | Dynamic CTQW-inspired signatures should place same-family graphs closer than different-family graphs. | `mean_interfamily_distance/mean_intrafamily_distance` | `1.1` | `1.0` | `inconclusive` | Dynamic-signature separation is below threshold. |
| `minello_2019` | `quantum_walk_signatures_support_graph_classification` | Quantum-walk dynamic signatures should classify graph families above baseline. | `group_split_accuracy` | `quantum>baseline and combined>=topology` | `quantum=0.000; topology=0.000; combined=0.000; baseline=0.000` | `inconclusive` | Classification is not sufficiently above controls. |
| `novo_2016` | `disorder_can_assist_suboptimal_transport` | Moderate disorder can improve transport in suboptimal regimes. | `max_arrival_delta_disorder_vs_clean_same_context` | `0.03` | `0.0` | `inconclusive` | No clean same-context disorder improvement above threshold was found. |
| `coates_2023` | `multiple_enaqt_optima_require_gamma_resolved_curves` | Some disordered networks can have more than one optimal noise regime rather than a single Goldilocks peak. | `gamma_resolved_peak_count` | `at least two separated local maxima` | `not exported by current summary-level campaign` | `inconclusive` | The current campaign stores best-point summaries, not full efficiency-versus-dephasing curves needed to count twin peaks. |
| `blach_2025` | `environment_assisted_transport_as_material_motivation` | Experiments can show best transport when disorder and dephasing are balanced. | `effective_model_dephasing_disorder_window` | `persistent positive dephasing gain with high-noise suppression` | `persistent=True; suppression=True` | `matched` | The effective model reproduces the qualitative balanced-regime motif, not the perovskite microscopic experiment. |
| `blach_2025` | `perovskite_nanocrystal_microscopic_reproduction` | A perovskite experiment requires material-specific structure, temperature dependence, and exciton parameters. | `model_scope` | `material-specific parameters required` | `effective network model only` | `not_applicable` | This lab uses controlled effective networks and does not yet include perovskite nanocrystal parameters. |
| `rojo_francas_2024` | `fractal_geometry_changes_transport_exponents` | Fractal lattices can show anomalous spreading governed by geometry and spectral structure. | `fractal_family_and_msd_exponent` | `fractal lattice family with fitted MSD exponent` | `fractal media not implemented in this campaign` | `not_applicable` | Fractal lattices are a valuable next extension, but the current campaign uses chains, rings, random graphs, and regular/effective media. |
| `gamble_2010` | `two_particle_quantum_walk_graph_isomorphism` | Interacting two-particle quantum walks can distinguish graph structures beyond some single-particle invariants. | `particle_number` | `two-particle interacting walk required` | `single-excitation effective model` | `not_applicable` | The current lab intentionally stays in the single-excitation sector, so this paper is a limitation guardrail rather than a direct benchmark. |
| `engel_2007` | `photosynthetic_wavelike_coherence_experimental_motivation` | Spectroscopic experiments can reveal coherent excitation dynamics in photosynthetic complexes. | `experimental_spectroscopy_scope` | `microscopic photosynthetic complex and spectroscopy required` | `effective graph transport model` | `not_applicable` | This paper motivates coherent excitation transport but is not reproduced by a generic graph model. |
| `maier_2019` | `finite_network_coherent_assisted_damped_progression` | Finite controlled networks can show coherent, assisted, and high-noise-damped regimes. | `finite_size_grid_plus_dephasing_window_plus_suppression` | `finite N and dephasing window with suppression` | `N=[8, 10, 12]; window=True; suppression=True` | `matched` | The effective finite-network model reproduces the qualitative regime progression. |
| `maier_2019` | `exact_10_qubit_hardware_reproduction` | Exact trapped-ion/qubit hardware reproduction would require microscopic hardware parameters. | `model_scope` | `hardware-specific parameters required` | `effective network model only` | `not_applicable` | This lab tests a qualitative finite-network analogue, not the experimental hardware implementation. |

## Figures

![Paper verdict overview](figures/paper_verdict_overview.png)

![Claim confidence](figures/paper_claim_confidence.png)

## Interpretation Rule

- `matched`: the expected direction appears and passes the stated threshold.
- `diverged`: the opposite direction appears with enough support.
- `inconclusive`: the current profile is under-resolved or the effect is below threshold.
- `not_applicable`: the current effective model lacks the required microscopic detail.

## Next Action

Run the `paper` profile if this was a smoke run. Run `confirm` only for claims that remain strong, divergent, or scientifically important but inconclusive.
