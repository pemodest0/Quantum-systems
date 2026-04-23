# Ring ceiling campaign

Generated at UTC: 2026-04-21T01:51:50.311351+00:00
Goal: test whether the unfavorable target eventually turns down at stronger phase scrambling.

## Literature guardrails

- Mohseni2008: https://doi.org/10.1063/1.3002335 -- Moderate dephasing can improve transport when coherent motion gets trapped by interference or disorder.
- PlenioHuelga2008: https://doi.org/10.1088/1367-2630/10/11/113019 -- There is typically an assistance window at weak or moderate noise, followed by suppression at stronger noise.
- Rebentrost2009: https://doi.org/10.1088/1367-2630/11/3/033003 -- A sink-efficiency scan over disorder and dephasing is the standard diagnosis for environment-assisted transport.
- Maier2019: https://doi.org/10.1103/PhysRevLett.122.050501 -- Experiments support a progression from coherent motion to assistance and then suppression at stronger noise.

## What was measured

- Favorable target mean gain over the scan stayed small: max gain = 0.023.
- Unfavorable target showed a much larger gain: max gain = 0.158.
- Unfavorable target best phase-scrambling values stayed in the moderate range, with maximum 0.80.

## Agreement with literature

- This agrees with the literature if the unfavorable target improves under moderate phase scrambling while the favorable target stays near the coherent optimum.
- Ceiling reached status: yes.

## What is still not proven

- If the unfavorable-target curve has not bent down by the end of the scan, the full assistance window is still not proven.
- This campaign uses 16 seeds, so it is suitable for interactive review but not yet the final confirmatory run.

## Derived table

| scenario | disorder | zero scrambling | best arrival | gain | best phase scrambling | spread |
| --- | --- | --- | --- | --- | --- | --- |
| favorable target | 0.40 | 0.697 | 0.697 | 0.000 | 0.00 | 0.054 |
| favorable target | 0.50 | 0.675 | 0.675 | 0.000 | 0.00 | 0.060 |
| favorable target | 0.60 | 0.654 | 0.654 | 0.000 | 0.00 | 0.066 |
| favorable target | 0.70 | 0.632 | 0.632 | 0.000 | 0.00 | 0.072 |
| favorable target | 0.80 | 0.608 | 0.608 | 0.000 | 0.00 | 0.079 |
| favorable target | 0.90 | 0.582 | 0.582 | 0.000 | 0.00 | 0.087 |
| favorable target | 1.00 | 0.557 | 0.557 | 0.000 | 0.00 | 0.092 |
| favorable target | 1.20 | 0.510 | 0.513 | 0.003 | 0.16 | 0.037 |
| favorable target | 1.40 | 0.460 | 0.484 | 0.023 | 0.40 | 0.032 |
| unfavorable target | 0.40 | 0.369 | 0.521 | 0.153 | 0.60 | 0.004 |
| unfavorable target | 0.50 | 0.368 | 0.520 | 0.152 | 0.60 | 0.006 |
| unfavorable target | 0.60 | 0.369 | 0.517 | 0.149 | 0.60 | 0.009 |
| unfavorable target | 0.70 | 0.371 | 0.514 | 0.144 | 0.60 | 0.011 |
| unfavorable target | 0.80 | 0.371 | 0.511 | 0.140 | 0.60 | 0.013 |
| unfavorable target | 0.90 | 0.367 | 0.506 | 0.140 | 0.60 | 0.016 |
| unfavorable target | 1.00 | 0.359 | 0.502 | 0.143 | 0.60 | 0.018 |
| unfavorable target | 1.20 | 0.340 | 0.490 | 0.151 | 0.60 | 0.024 |
| unfavorable target | 1.40 | 0.319 | 0.477 | 0.158 | 0.80 | 0.024 |
