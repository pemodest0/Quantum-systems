# Transport Graph Lab

This laboratory layer is the editable simulation environment for the MSc project
`Coherent and Dissipative Transport in Simple Open Quantum Networks`.

## What it does

It compares small graph topologies under the same open-system model:

- `chain`
- `ring`
- `complete`

The main observable is:

- `sink efficiency`

The secondary observables are:

- `population dynamics`
- `coherence`

## What the sink means

The `sink` is an absorbing target state that represents successful transport.

- It is not an extra physical node of the graph.
- It collects population from the chosen trap site.
- Its final population is the transport success metric.

This is useful because it separates:

- coherent motion inside the graph;
- successful transport to the target;
- parasitic loss.

## Editable configuration

The file to edit is:

```text
configs/transport_graph_lab_config.json
```

Additional tested presets:

```text
configs/transport_graph_lab_extended_nodes.json
configs/transport_graph_lab_high_loss.json
```

Important fields:

- `seed`: controls the random disorder realization.
- `n_sites`: number of graph nodes.
- `topology`: `chain`, `ring`, or `complete`.
- `initial_site`: where the excitation starts.
- `trap_site`: site connected to the sink.
- `coupling_hz`: coherent hopping scale.
- `sink_rate_hz`: capture rate into the sink.
- `loss_rate_hz`: parasitic loss rate.
- `disorder_strength_hz`: static on-site disorder strength.
- `dephasing_rates_hz`: scan grid for the dephasing rate.
- `visualization.animation_stride`: animation frame skipping factor.
- `visualization.animation_fps`: GIF playback rate.

## Run

From the repository root:

```powershell
$env:PYTHONPATH='src'
python scripts\run_transport_graph_lab.py
```

Inside VS Code you can also use:

```text
Terminal -> Run Task
```

and select one of:

```text
Transport Lab: Run default graph study
Transport Lab: Run extended-nodes preset
Transport Lab: Run high-loss preset
Transport Lab: Run proposal lab summary
Transport Lab: Build demo PDF
```

## Main artifacts

```text
outputs/transport_networks/graph_lab/latest/figures/sink_efficiency_by_graph.png
outputs/transport_networks/graph_lab/latest/figures/population_dynamics_by_graph.png
outputs/transport_networks/graph_lab/latest/figures/coherence_by_graph.png
outputs/transport_networks/graph_lab/latest/figures/graph_topology_overview.png
outputs/transport_networks/graph_lab/latest/figures/*_topology.png
outputs/transport_networks/graph_lab/latest/animations/*_population_evolution.gif
outputs/transport_networks/graph_lab/latest/comparative_table.csv
outputs/transport_networks/graph_lab/latest/comparative_table.md
outputs/transport_networks/graph_lab/latest/SINK_EXPLANATION.md
outputs/transport_networks/graph_lab/latest/results.json
outputs/transport_networks/graph_lab/latest/metrics.json
```

## Visual layer

The lab now generates:

- a topology overview image for the current graph set;
- one static topology image per scenario;
- one GIF animation per scenario showing population flow in the best regime.

This is meant to make the lab feel closer to a virtual experiment: you edit the
configuration, run the simulation, and inspect both the quantitative plots and
the graph evolution directly.

## PDF demo

To regenerate the explanatory PDF for the current baseline:

```powershell
$env:PYTHONPATH='src'
python scripts\build_transport_graph_lab_demo.py --json
```

Output:

```text
reports/transport_graph_lab_demo/transport_graph_lab_demo.pdf
```
