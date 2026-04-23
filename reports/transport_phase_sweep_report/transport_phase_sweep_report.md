# Transport Phase-Slice Report

## Scope

This report summarizes a systematic set of transport simulations on the three graph families currently implemented in the laboratory:

- chain
- ring
- complete graph

The controlled parameter sweeps are:

- number of sites `N`
- sink ratio `kappa/J`
- loss ratio `Gamma/J`
- disorder ratio `W/J`

For every simulated point, the code scans the dephasing rate `gamma_phi` and records:

- the best sink efficiency `eta_best`
- the optimal dephasing rate `gamma_phi_best`
- the coherence at the optimum
- the loss at the optimum
- the numerical diagnostics of the master-equation integration

## How to read the physics correctly

The graph is the physical connectivity architecture of the effective open quantum system.

- A node `i` is a local basis state `|i>`.
- An edge `(i,j)` is a coherent hopping channel with amplitude `J_ij`.
- The sink is an absorbing success channel.
- The loss channel is parasitic dissipation.

The main success metric is:

`eta(T) = rho_ss(T)`

This is the final sink population. It is the correct transport observable because it measures successful arrival at the target, not just spreading over the graph.

The site populations are:

`P_i(t) = rho_ii(t)`

The coherence measure is:

`C_l1(rho) = sum_(i!=j) |rho_ij|`

### Uncertainty

For clean graphs, the model is deterministic, so the uncertainty is zero by construction.

For disordered graphs, the uncertainty bands and standard deviations come from an ensemble over static-disorder realizations. This is not measurement noise. It is configuration-to-configuration spread induced by random site energies.

Important caution: in the current phase-slice study the disorder ensemble uses only four seeds. That is enough for a pilot map and for detecting robust trends, but it is not enough for a publishable uncertainty analysis. Any paper-quality disorder claim must be repeated with a denser disorder ensemble.

### Numerical correctness

Every case stores:

- maximum trace deviation
- maximum population-closure error
- minimum density-matrix eigenvalue

In the present dataset these diagnostics remain near machine precision, so the populations are numerically trustworthy.

## Literature basis already anchoring the project

1. Mohseni et al. (2008), *Environment-assisted quantum walks in photosynthetic energy transfer*.
   DOI: `10.1063/1.3002335`
   Why it matters: Seminal ENAQT starting point.

2. Plenio and Huelga (2008), *Dephasing-assisted transport: Quantum networks and biomolecules*.
   DOI: `10.1088/1367-2630/10/11/113019`
   Why it matters: Clean conceptual argument for why moderate dephasing can help transport.

3. Rebentrost et al. (2009), *Environment-assisted quantum transport*.
   DOI: `10.1088/1367-2630/11/3/033003`
   Why it matters: Core ENAQT formulation linking coherent transport and noise optimization.

4. Caruso et al. (2009), *Highly efficient energy excitation transfer in light-harvesting complexes: The fundamental role of noise-assisted transport*.
   DOI: `10.1063/1.3223548`
   Why it matters: Strong benchmark on the interplay between transport efficiency and dephasing.

5. Whitfield et al. (2010), *Quantum stochastic walks: A generalization of classical random walks and quantum walks*.
   DOI: `10.1103/PhysRevA.81.022323`
   Why it matters: Useful if the project later moves from local Lindblad terms to graph-defined open walks.

6. Caruso et al. (2011), *Simulation of noise-assisted transport via optical cavity networks*.
   DOI: `10.1103/PhysRevA.83.013811`
   Why it matters: Experimental bridge between abstract transport models and engineered platforms.

7. Zimboras et al. (2013), *Quantum Transport Enhancement by Time-Reversal Symmetry Breaking*.
   DOI: `10.1038/srep02361`
   Why it matters: Shows that transport is also shaped by graph phases and directionality, not only by dephasing.

8. Caruso (2014), *Universally optimal noisy quantum walks on complex networks*.
   DOI: `10.1088/1367-2630/16/5/055015`
   Why it matters: One of the strongest topology-dependent references already aligned with this project.

9. Li et al. (2015), *'Momentum rejuvenation' underlies the phenomenon of noise-assisted quantum energy flow*.
   DOI: `10.1088/1367-2630/17/1/013057`
   Why it matters: Useful physical interpretation of why moderate noise can unlock transport.

10. Viciani et al. (2015), *Observation of Noise-Assisted Transport in an All-Optical Cavity-Based Network*.
   DOI: `10.1103/PhysRevLett.115.083601`
   Why it matters: Experimental anchor for ENAQT.

11. Caruso et al. (2016), *Fast escape of a quantum walker from an integrated photonic maze*.
   DOI: `10.1038/ncomms11682`
   Why it matters: Directly relevant when topology and trapping geometry become part of the question.

12. Maier et al. (2019), *Environment-Assisted Quantum Transport in a 10-qubit Network*.
   DOI: `10.1103/PhysRevLett.122.050501`
   Why it matters: Direct multi-qubit transport benchmark with controlled noise.

13. Alterman et al. (2024), *Optimal conditions for environment-assisted quantum transport on the fully connected network*.
   DOI: `10.1103/PhysRevE.109.014310`
   Why it matters: Directly relevant to the complete-graph branch of the present study.

## Twelve additional papers worth using next

1. Chin et al. (2010), *Noise-assisted energy transfer in quantum networks and light-harvesting complexes*.
   DOI: `10.1088/1367-2630/12/6/065002`
   Why it matters: Explains concrete noise-enabled pathways and is useful for interpreting why a topology changes its preferred dephasing window.

2. Hoyer, Sarovar, and Whaley (2010), *Limits of quantum speedup in photosynthetic light harvesting*.
   DOI: `10.1088/1367-2630/12/6/065041`
   Why it matters: Important guardrail against overclaiming that coherence alone always improves transport.

3. Mulken and Blumen (2011), *Continuous-time quantum walks: Models for coherent transport on complex networks*.
   DOI: `10.1016/j.physrep.2011.01.002`
   Why it matters: Core review for graph-based coherent transport, traps, disorder, and complex-network geometry.

4. Scholak et al. (2011), *Efficient and coherent excitation transfer across disordered molecular networks*.
   DOI: `10.1103/PhysRevE.83.021912`
   Why it matters: Directly relevant to ensemble disorder and structure-performance relations.

5. Hoyer, Ishizaki, and Whaley (2012), *Spatial propagation of excitonic coherence enables ratcheted energy transfer*.
   DOI: `10.1103/PhysRevE.86.041911`
   Why it matters: Useful when discussing how coherence can direct transport, not only speed it up.

6. Manzano (2013), *Quantum transport in networks and photosynthetic complexes at the steady state*.
   DOI: `10.1371/journal.pone.0057041`
   Why it matters: Important if the project later compares transient sink efficiency with driven steady-state transport.

7. Novo et al. (2016), *Disorder-assisted quantum transport in suboptimal decoherence regimes*.
   DOI: `10.1038/srep18142`
   Why it matters: Directly aligned with the current disorder sweeps and crossover logic.

8. Cabot et al. (2018), *Unveiling noiseless clusters in complex quantum networks*.
   DOI: `10.1038/s41534-018-0108-9`
   Why it matters: Relevant for understanding when topology creates protected or weakly damped transport sectors.

9. Souza and Andrade (2019), *Fast and slow dynamics for classical and quantum walks on mean-field small world networks*.
   DOI: `10.1038/s41598-019-55580-2`
   Why it matters: Gives a concrete entry point if the project expands from ring and complete graphs to small-world connectivity.

10. Razzoli et al. (2021), *Transport Efficiency of Continuous-Time Quantum Walks on Graphs*.
   DOI: `10.3390/e23010085`
   Why it matters: Direct graph-by-graph reference, especially useful for bridge, bottleneck, and joined-complete structures.

11. Dudhe, Sahoo, and Benjamin (2022), *Testing quantum speedups in exciton transport through a photosynthetic complex using quantum stochastic walks*.
   DOI: `10.1039/D1CP02727A`
   Why it matters: Relevant if the project later needs a hybrid coherent-incoherent walk language for comparison.

12. Coutinho et al. (2022), *Robustness of noisy quantum networks*.
   DOI: `10.1038/s42005-022-00866-7`
   Why it matters: Not an ENAQT paper, but useful if the project later connects topology to robustness metrics and network failure modes.

## What was simulated

The current study is not yet a full four-dimensional phase diagram. It is a controlled set of phase slices.

### 1. Size sweep

The number of sites `N` was varied while keeping the other parameters fixed.

#### Chain

- `N=4.0`: best regime = `coherent`, eta_best = `0.848`, gamma_phi_best = `0.000`
- `N=5.0`: best regime = `coherent`, eta_best = `0.805`, gamma_phi_best = `0.000`
- `N=6.0`: best regime = `coherent`, eta_best = `0.759`, gamma_phi_best = `0.000`
- `N=7.0`: best regime = `coherent`, eta_best = `0.733`, gamma_phi_best = `0.000`

Interpretation: in this protocol the clean chain stays coherent-optimal across the scanned sizes, and the best transport efficiency decreases with system size.

#### Ring

- `N=4.0`: best regime = `coherent`, eta_best = `0.897`, gamma_phi_best = `0.000`
- `N=5.0`: best regime = `intermediate`, eta_best = `0.709`, gamma_phi_best = `0.800`
- `N=6.0`: best regime = `coherent`, eta_best = `0.851`, gamma_phi_best = `0.000`
- `N=7.0`: best regime = `intermediate`, eta_best = `0.583`, gamma_phi_best = `0.400`

Interpretation: the ring shows a strong size dependence, including an alternation between coherent and intermediate optimal regimes in the scanned set. That makes ring parity and sink placement an immediate next target.

#### Complete graph

- `N=4.0`: best regime = `intermediate`, eta_best = `0.767`, gamma_phi_best = `3.200`
- `N=5.0`: best regime = `intermediate`, eta_best = `0.690`, gamma_phi_best = `3.200`
- `N=6.0`: best regime = `strongly_dissipative`, eta_best = `0.619`, gamma_phi_best = `6.400`
- `N=7.0`: best regime = `strongly_dissipative`, eta_best = `0.567`, gamma_phi_best = `6.400`

Interpretation: the complete graph prefers intermediate dephasing at smaller sizes and moves toward the largest scanned dephasing at larger sizes.

### 2. Sink-rate sweep `kappa/J`

Main result:

- chain remains coherent-optimal throughout the scan;
- ring remains intermediate-optimal throughout the scan;
- complete graph remains intermediate-optimal throughout the scan.

Physical meaning:

- increasing `kappa/J` improves best sink efficiency in all topologies because the target captures population more aggressively once the excitation reaches the trap;
- however, the topology determines whether coherence or dephasing helps that arrival happen in the first place.

### 3. Loss-rate sweep `Gamma/J`

Main result:

- increasing `Gamma/J` lowers `eta_best` for every topology;
- the regime classification is stable across the scanned loss values:
  - chain stays coherent-optimal;
  - ring stays intermediate-optimal;
  - complete stays intermediate-optimal.

Physical meaning:

- larger parasitic loss drains population before it can reach the sink;
- in this scan, loss changes efficiency strongly but does not change the basic mechanism that optimizes transport.

### 4. Disorder sweep `W/J`

#### Chain

- `W/J=0.0`: best regime = `coherent`, eta_best = `0.805`, gamma_phi_best = `0.000`
- `W/J=0.2`: best regime = `coherent`, eta_best = `0.799 +/- 0.009`, gamma_phi_best = `0.000`
- `W/J=0.4`: best regime = `coherent`, eta_best = `0.779 +/- 0.023`, gamma_phi_best = `0.000`
- `W/J=0.8`: best regime = `intermediate`, eta_best = `0.715 +/- 0.021`, gamma_phi_best = `0.100`

Interpretation: the chain remains coherent-optimal at weak disorder, but crosses into an intermediate optimum at strong disorder.

#### Ring

- `W/J=0.0`: best regime = `intermediate`, eta_best = `0.709`, gamma_phi_best = `0.800`
- `W/J=0.2`: best regime = `intermediate`, eta_best = `0.714 +/- 0.006`, gamma_phi_best = `0.800`
- `W/J=0.4`: best regime = `intermediate`, eta_best = `0.717 +/- 0.014`, gamma_phi_best = `0.800`
- `W/J=0.8`: best regime = `intermediate`, eta_best = `0.720 +/- 0.055`, gamma_phi_best = `0.400`

Interpretation: the ring remains intermediate-optimal, but the uncertainty broadens significantly at larger disorder.

#### Complete graph

- `W/J=0.0`: best regime = `intermediate`, eta_best = `0.690`, gamma_phi_best = `3.200`
- `W/J=0.2`: best regime = `intermediate`, eta_best = `0.690 +/- 0.002`, gamma_phi_best = `3.200`
- `W/J=0.4`: best regime = `intermediate`, eta_best = `0.690 +/- 0.003`, gamma_phi_best = `3.200`
- `W/J=0.8`: best regime = `intermediate`, eta_best = `0.689 +/- 0.007`, gamma_phi_best = `3.200`

Interpretation: the complete graph is remarkably robust in this sweep. The optimal dephasing rate stays fixed and the best efficiency changes very little.

## What we are doing correctly

The current protocol is correct in the following sense:

1. We are not confusing graph occupancy with successful transport.
   - Success is measured by sink population, not by arbitrary spreading on the network.

2. We are not hiding parasitic dissipation.
   - Loss is modeled explicitly through a separate absorbing channel.

3. We are checking numerical consistency.
   - Trace and population closure stay at machine precision.

4. We are separating deterministic effects from disorder uncertainty.
   - Clean cases have no artificial uncertainty bands.
   - Disordered cases report ensemble spread across seeds.

5. We are not overclaiming a full phase diagram yet.
   - What we currently have is a systematic set of phase slices in controlled dimensionless variables.

## What is robust already

- The chain is coherent-optimal over the clean `N` sweep currently sampled.
- The complete graph remains dephasing-assisted across the clean `kappa/J`, `Gamma/J`, and `W/J` slices already sampled.
- Increasing `Gamma/J` always hurts transport in the sampled window.
- Sink and loss have been separated correctly, so `eta_best` is a transport-success metric, not a survival metric.

## What is promising but not yet a paper claim

- The ring alternation with `N` may encode a genuine parity or sink-placement effect, but the present scan is still too sparse to claim a structural law.
- The chain crossover near strong disorder looks real, but the `W/J` grid is still too coarse to locate a precise boundary.
- The complete graph looks unusually robust against diagonal disorder, but this must be checked for larger `N`, more seeds, and additional sink placements.

## Plausible publishable findings

These are not claims of novelty yet. They are the strongest candidate outcomes if the next simulations confirm them.

### Candidate finding 1: disorder-induced crossover in the chain

In the present protocol, the chain changes from coherent-optimal to intermediate-optimal only once the disorder becomes strong enough.

Why this matters:

- it suggests a concrete crossover line in the `(W/J, gamma_phi/J)` plane;
- it is simple to refine numerically;
- it is physically interpretable in terms of disorder blocking coherent transport and moderate dephasing reopening pathways.

### Candidate finding 2: robust intermediate optimum in the complete graph

The complete graph keeps the same qualitative optimum across the disorder sweep, and `eta_best` changes only weakly.

Why this matters:

- it suggests that high-connectivity topologies may be less sensitive to diagonal disorder under this protocol;
- that can become a clean robustness statement if confirmed with larger `N`, more seeds, and more than one trap placement.

### Candidate finding 3: topology-dependent scaling of the optimal regime

The three topologies do not scale in the same way with `N`.

- the chain stays coherent-optimal;
- the complete graph becomes increasingly dephasing-dependent;
- the ring shows strong size sensitivity.

Why this matters:

- this is closer to a structural transport law than to a single-case plot;
- it can become the backbone of a topology-dependent transport atlas.

### Candidate finding 4: robustness itself as an observable

The disordered ring has the largest uncertainty band among the scanned topologies.

Why this matters:

- average efficiency alone is not enough;
- topology-dependent variance can become a second axis of comparison;
- this is scientifically stronger than reporting only mean efficiencies.

## What to model next

The next step that is actually worth doing is not to add random exotic graph names. It is to refine the existing atlas in a disciplined way.

### Highest-priority numerical program

1. Refine the `W/J` grid around the chain crossover.
2. Refine the `N` grid for rings to test whether the current alternation is a parity effect or an artifact of source/sink placement.
3. Add sink-position sweeps at fixed topology.
4. Increase the disorder ensemble from 4 seeds to at least 32 for any figure that will be shown as an uncertainty statement.

### The first new models worth adding

1. `star` graph
   - Reason: it introduces hub centrality in the cleanest possible way.
   - Question: does a central sink favor coherent transport or dephasing-assisted transport?

2. `regular ring with range m > 1`
   - Reason: it interpolates between simple ring and denser connectivity without jumping directly to the complete graph.
   - Question: how much connectivity is needed before the preferred regime shifts?

3. `small-world rewired ring`
   - Reason: it adds shortcut structure while keeping a graph family with controllable disorder in topology itself.
   - Question: do shortcuts mimic dephasing-assisted unlocking, or do they replace it?

4. `joined complete graphs / bridge bottlenecks`
   - Reason: they provide a simple way to study transport through bottlenecks.
   - Question: does the optimum depend more on local degree or on graph bottleneck structure?

### The first graph metrics worth correlating with transport

- degree of the trap node
- average shortest-path distance to the trap
- closeness centrality of the trap
- graph diameter
- variance of node degree

## What would count as an original result

A publishable result here is not merely `one more plot of eta_best for three graphs`. The work starts to look original if it delivers one of the following in a reproducible way:

1. a topology-resolved regime atlas in normalized variables `(N, kappa/J, Gamma/J, W/J, gamma_phi/J)`;
2. a disorder-driven crossover line for the chain, with uncertainty bands and sink-position controls;
3. a centrality-versus-transport law showing how `gamma_phi_best` shifts with trap degree or distance;
4. a robustness ranking where both mean efficiency and ensemble variance are reported together.

## Bottom line

What we are doing right now is already scientifically coherent:

- the graph is the physical connectivity structure;
- the Hamiltonian defines coherent motion;
- Lindblad channels define dephasing, sink capture, and loss;
- the systematic sweeps tell us how transport regimes change with structure and environment.

The strongest near-term objective is:

**turn these phase slices into a real transport phase atlas, starting from `N`, `kappa/J`, `Gamma/J`, `W/J`, and then moving to sink placement, star graphs, and graph-metric correlations.**
