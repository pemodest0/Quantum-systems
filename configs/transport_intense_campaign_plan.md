# Intense Transport Campaign Plan

This campaign is designed for the Mac or an overnight run, not for normal use on the current PC.

## Profile

Script:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile intense
```

Output:

```text
outputs/transport_networks/dynamic_network_atlas_intense/latest/
```

## Grid

- Families: all dynamic network families in the lab.
- Sizes: `N = 8, 10, 12, 16`.
- Random graph realizations: `16` per random family and size.
- Deterministic graph realizations: `1` per deterministic family and size.
- Disorder strengths `W/J`: `0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5`.
- Disorder seeds: `24`.
- Dephasing strengths `gamma_phi/J`: `0.0, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.6`.
- Target styles: `near`, `far`, `high_centrality`, `low_centrality`.
- Final time: `18/J`.
- Time samples: `220`.

## Safe Chunked Runs

Run random families separately because they dominate the count:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile intense --families modular_two_community --resume
python scripts\run_transport_dynamic_network_atlas.py --profile intense --families random_geometric --resume
python scripts\run_transport_dynamic_network_atlas.py --profile intense --families watts_strogatz_small_world --resume
python scripts\run_transport_dynamic_network_atlas.py --profile intense --families erdos_renyi --resume
python scripts\run_transport_dynamic_network_atlas.py --profile intense --families barabasi_albert_scale_free --resume
```

Then run deterministic/special families:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile intense --families chain,ring,complete,star,square_lattice_2d,bottleneck,clustered,sierpinski_gasket,sierpinski_carpet_like --resume
```

## First 10k-Record Pilot Of The Intense Profile

This is not a smoke test. It is the first chunk of the real profile:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile intense --stop-after-records 10000 --resume
```

Continue later with:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile intense --resume
```

## After Completion

Rebuild the lab registry and MCP index:

```powershell
python scripts\run_transport_lab_master_pipeline.py --mode registry_only
python scripts\build_transport_lab_mcp_index.py
python scripts\run_transport_lab_mcp_server.py --check
```

## Scientific Gate

The campaign becomes evidence only if:

- numerical validation passes;
- CI95 is available by family and target;
- quantum-minus-classical is checked before claiming a quantum signature;
- dephasing assistance has positive CI95 and is not just spreading;
- the critic report does not block the claim.
