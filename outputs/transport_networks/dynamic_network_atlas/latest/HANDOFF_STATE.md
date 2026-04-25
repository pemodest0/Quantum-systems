## Strong Atlas Handoff State

Updated: 2026-04-25

This atlas run was started on the Windows PC with `--profile strong` and then paused for continuation on the Mac.

### Important state

- `atlas_records.csv` already contains `22050` records.
- `atlas_metrics.json`, `summary.md`, and the generated figures still reflect the last fully completed chunk at `14800` records.
- This mismatch is expected because the interrupted `random_geometric` run checkpointed records to CSV before the final summary-writing stage.

### Fully completed families

- `chain`
- `ring`
- `complete`
- `star`
- `square_lattice_2d`
- `bottleneck`
- `clustered`
- `sierpinski_gasket`
- `sierpinski_carpet_like`
- `modular_two_community`

### Partially started family

- `random_geometric`
- checkpointed records currently present: `7250`

### Exact next command on the Mac

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile strong --families random_geometric --resume
```

After `random_geometric`, continue with:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile strong --families watts_strogatz_small_world --resume
python scripts\run_transport_dynamic_network_atlas.py --profile strong --families erdos_renyi --resume
python scripts\run_transport_dynamic_network_atlas.py --profile strong --families barabasi_albert_scale_free --resume
python scripts\run_transport_dynamic_network_atlas.py --profile strong --resume
python scripts\run_transport_lab_master_pipeline.py --mode registry_only
python scripts\build_transport_lab_mcp_index.py
python scripts\run_transport_lab_mcp_server.py --check
```

### Interpretation rule

Do not treat the current `atlas_metrics.json` or figures as final until the full normalization pass (`--profile strong --resume`) finishes.
