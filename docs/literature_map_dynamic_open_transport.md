# Literature Map: Dynamic Open Quantum Transport On Networks

Generated for the current research track on dynamic fingerprints of open quantum transport.

## Scope

The project is not trying to model one microscopic material in full detail. The central scope is:

> finite networks where a single excitation moves coherently, is affected by disorder and dephasing, and is captured by a target channel.

The literature was mapped around four concentric themes:

1. continuous-time quantum walks on graphs;
2. open/noisy transport and environment-assisted quantum transport;
3. target/trap placement and transport efficiency;
4. graph similarity/classification from quantum-walk dynamics.

## Conservative Volume Estimate

These counts are approximate and intentionally conservative. They come from OpenAlex title searches, so they undercount papers whose title does not contain the exact phrase, but they avoid the huge false-positive counts produced by broad keyword search.

| Query | Conservative title-level count | How to read it |
| --- | ---: | --- |
| `continuous-time quantum walk` | 348 | Broad foundation literature. |
| `quantum stochastic walk` | 46 | Open/interpolating walk literature. |
| `environment-assisted quantum transport` | 22 | Core ENAQT phrase. |
| `dephasing-assisted transport` | 16 | More specific noise-assisted transport phrase. |
| `quantum walk graph kernel` | 8 | Quantum-walk graph-kernel literature. |
| `quantum Jensen-Shannon graph kernel` | 6 | Specific graph-kernel branch. |
| `quantum walk graph similarity` | 5 | Directly relevant to graph comparison. |
| `disorder-assisted quantum transport` | 4 | Specific disorder-assisted branch. |
| `quantum walk graph classification` | 2 | Exact title phrase is rare. |
| `transport efficiency continuous-time quantum walks graphs` | 1 | Very close to our trap/topology benchmark. |

Practical interpretation:

- Total broad field: hundreds of CTQW/open-walk papers.
- Directly relevant project-level literature: about 80-120 papers after filtering.
- High-value papers worth reading/citing carefully: about 30-45.
- Core papers that should drive the simulations and report: about 12-18.

## Tier A: Must Drive The Project

These are the papers that should define the methods, controls, and benchmark language.

| Priority | Paper | Role in our project |
| --- | --- | --- |
| A1 | Muelken & Blumen, 2011, `Continuous-time quantum walks: Models for coherent transport on complex networks`, DOI `10.1016/j.physrep.2011.01.002` | Main CTQW review. Defines graph transport, traps, disorder, long-range interactions, and classical-vs-quantum contrast. |
| A2 | Razzoli, Paris & Bordone, 2021, `Transport Efficiency of Continuous-Time Quantum Walks on Graphs`, DOI `10.3390/e23010085` | Direct benchmark for graph topology, initial state, target/trap placement, and why degree/connectivity alone is not enough. |
| A3 | Plenio & Huelga, 2008, `Dephasing-assisted transport: quantum networks and biomolecules`, DOI `10.1088/1367-2630/10/11/113019` | Core source for dephasing helping transport. |
| A4 | Mohseni et al., 2008, `Environment-Assisted Quantum Walks in Photosynthetic Energy Transfer`, DOI `10.1063/1.3002335` | Core source for environment-assisted transport using open quantum dynamics. |
| A5 | Rebentrost et al., 2009, `Environment-assisted quantum transport`, DOI `10.1088/1367-2630/11/3/033003` | Main ENAQT scan logic: disorder, dephasing, trapping, efficiency. |
| A6 | Caruso et al., 2009, `Highly efficient energy excitation transfer...`, DOI `10.1063/1.3223548` | Mechanistic explanation: noise can break destructive interference and open transport pathways. |
| A7 | Novo et al., 2016, `Disorder-assisted quantum transport in suboptimal decoherence regimes`, DOI `10.1038/srep18142` | Important for the disorder/dephasing maps and for not treating disorder as always harmful. |
| A8 | Whitfield, Rodriguez-Rosario & Aspuru-Guzik, 2010, `Quantum stochastic walks`, DOI `10.1103/PhysRevA.81.022323` | Formal bridge between classical random walks and quantum walks. Justifies our classical control comparison. |
| A9 | Rossi, Torsello & Hancock, 2015, `Measuring graph similarity through CTQW and quantum Jensen-Shannon divergence`, DOI `10.1103/PhysRevE.91.022815` | Direct support for using quantum-walk dynamics as graph fingerprints. |
| A10 | Minello, Rossi & Torsello, 2019, `Can a Quantum Walk Tell Which Is Which?`, DOI `10.3390/e21030328` | Direct support for graph similarity/classification using quantum-walk evolution. |
| A11 | Maier et al., 2019, `Environment-Assisted Quantum Transport in a 10-qubit Network`, DOI `10.1103/PhysRevLett.122.050501` | Experimental anchor: controlled open quantum transport in a finite network. |
| A12 | QSWalk, 2017, DOI `10.1016/j.cpc.2017.03.014` | Computational reference for quantum stochastic walks on arbitrary graphs. |
| A13 | Kendon, 2007, `Decoherence in quantum walks: a review`, DOI `10.1017/S0960129507006354` | Broad guardrail for decoherence as a tunable part of quantum-walk dynamics, not only an error source. |
| A14 | Coates, Lovett & Gauger, 2023, `From Goldilocks to twin peaks`, DOI `10.1039/D2CP04935J` | Warns that ENAQT can have multiple useful noise regimes; motivates saving full dephasing curves, not only best points. |
| A15 | Blach et al., 2025, `Environment-assisted quantum transport of excitons in perovskite nanocrystal superlattices`, DOI `10.1038/s41467-024-55812-8` | Modern experimental motivation for balanced disorder/dephasing transport; use only as motivation unless material parameters are added. |

## Tier B: Important Context And Extensions

These papers should be cited selectively when the corresponding point appears in the text.

| Paper | Use |
| --- | --- |
| Shabani et al., 2014, `Numerical evidence for robustness of environment-assisted quantum transport`, DOI `10.1103/PhysRevE.89.042706` | Robustness over parameters and ensemble thinking. |
| Novo et al., 2015, `Systematic Dimensionality Reduction for Quantum Walks`, DOI `10.1038/srep13304` | Non-regular graph transport and search; useful for reduced models and symmetry. |
| Muelken, Pernice & Blumen, 2007, CTQW on small-world networks, DOI `10.1103/PhysRevE.76.051125` | Specific support for small-world topology. |
| Alterman, Berman & Strauch, 2024, `Optimal conditions for ENAQT on the fully connected network`, DOI `10.1103/PhysRevE.109.014310` | Modern analytic reference for complete graphs and dephasing/trapping. |
| Bressanini, Benedetti & Paris, 2022, decoherence/classicalization in quantum walks | Useful for explaining transition from coherent to classical-like dynamics. |
| Wang et al., 2022, `CTQW based centrality testing on weighted graphs`, DOI `10.1038/s41598-022-09915-1` | Supports weighted graphs and quantum-walk centrality ideas. |
| Bai et al., 2014, `Quantum Jensen-Shannon graph kernel`, DOI `10.1016/j.patcog.2014.03.028` | Graph-kernel background for ML comparison. |
| Quantum walk graph kernels, 2013-2025 line | Relevant if we later formalize a graph kernel from our dynamics. |
| Rojo-Francas et al., 2024, anomalous quantum transport in fractal lattices, DOI `10.1038/s42005-024-01747-x` | Future geometry extension: fractal networks and MSD exponents. |
| Gamble et al., 2010, two-particle quantum walks for graph isomorphism, DOI `10.1103/PhysRevA.81.052313` | Limitation guardrail: single-excitation dynamics is not the whole graph-distinguishability story. |
| Engel et al., 2007, wavelike energy transfer in photosynthetic systems, DOI `10.1038/nature05678` | Experimental motivation for coherent excitation dynamics; not a direct graph-model benchmark. |
| Perovskite ENAQT, Nature Communications 2025 | Experimental motivation only; do not overclaim material realism. |
| Photonic decoherence-control ENAQT experiments | Experimental motivation for controlled dephasing. |

## Tier C: Optional Or Future

Use these only if the project expands.

| Theme | Keep for later because |
| --- | --- |
| Full photosynthetic-complex microscopic modeling | Too material-specific for the current mestrado scope. |
| Superconducting-circuit microscopic modeling | Good future motivation, but not needed for the first article. |
| Directed graph quantum walks | Useful later; current Hamiltonian and Lindblad setup assumes symmetric coupling. |
| Discrete-time quantum walks | Interesting, but current lab is continuous-time/open-system. |
| Quantum algorithms/search on exotic graphs | Context only unless we pivot to quantum algorithms. |
| Hybrid discrete-continuous quantum walks | New and interesting, but not central to current validation. |

## Papers To Reproduce Or Benchmark Directly

The computational lab should map each core paper to a concrete test.

| Benchmark | Paper anchor | What to reproduce |
| --- | --- | --- |
| Closed coherent spreading | Muelken & Blumen 2011 | Return probability, participation/spreading, topology dependence, no sink/loss. |
| Target/trap placement | Razzoli 2021 | Same graph and initial site, vary only target; show efficiency changes. |
| Dephasing-assisted window | Plenio-Huelga 2008; Mohseni 2008; Rebentrost 2009 | Efficiency vs dephasing, with zero-noise control and high-noise suppression. |
| Disorder-assisted behavior | Novo 2016; Shabani 2014 | Ensemble over disorder seeds; report mean and confidence interval. |
| Quantum vs classical control | Whitfield 2010 | Compare CTQW/open quantum dynamics against classical continuous-time rate walk. |
| Dynamic graph fingerprint | Rossi 2015; Minello 2019 | Show whether dynamic signatures classify graph families beyond topology-only controls. |
| Experimental plausibility | Maier 2019 | Use as motivation for finite controlled networks, not as proof of our exact model. |
| Multiple-noise-optimum check | Coates 2023 | Export full efficiency-versus-dephasing curves and count separated local maxima. |
| Material-motivation guardrail | Blach 2025; Engel 2007 | Say what the effective model can and cannot claim about real excitonic materials. |
| Exotic geometry guardrail | Rojo-Francas 2024 | Add fractal networks only after the current graph-family benchmarks are stable. |

## What Adds Most To Our Current Project

Best fit for the current results:

1. Razzoli 2021: directly supports the claim that target placement is a first-order variable.
2. Muelken & Blumen 2011: gives the general CTQW/complex-network foundation.
3. Plenio-Huelga 2008, Mohseni 2008, Rebentrost 2009: justify dephasing-assisted transport.
4. Whitfield 2010: justifies comparing against classical random/rate walks.
5. Rossi 2015 and Minello 2019: justify classification/similarity from quantum-walk dynamics.
6. Novo 2016 and Shabani 2014: justify disorder ensembles and robustness checks.
7. Maier 2019: gives experimental credibility for finite controlled networks.

## Current Project Positioning

The strongest article/proposal sentence should be:

> We study whether dynamic signatures of open quantum transport classify finite network topologies and reveal regimes where dephasing, disorder, and target placement enhance or suppress useful arrival.

This is more defensible than saying:

> We simulate real materials.

and more original than saying:

> We plot transport efficiency on a few graphs.

## Immediate Reading Order

Read in this order:

1. Muelken & Blumen 2011.
2. Razzoli 2021.
3. Plenio & Huelga 2008.
4. Mohseni 2008.
5. Rebentrost 2009.
6. Whitfield 2010.
7. Rossi 2015.
8. Minello 2019.
9. Novo 2016.
10. Maier 2019.
11. Kendon 2007.
12. Caruso 2009.
13. Coates 2023.
14. Blach 2025.

After the first ten, the project has enough literature spine for a serious MSc proposal and an initial paper draft. Items 11-14 are the next layer for refinement, modern context, and guardrails.
