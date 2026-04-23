# Workspace Repo Map

This file explains how the broader workspace is divided so a new agent does not mix projects.

## Source of truth for the open quantum transport lab

- `repos/Quantum-systems`

This is the repository that contains:

- the open quantum transport lab;
- the paper reproduction suite;
- the atlas/evidence-prep/intense campaign scripts;
- the lab registry and MCP index;
- the notebooks and reports used for the current transport research line.

If the task is about open quantum systems transport, this is the primary repository.

## Related repositories in the same workspace

- `repos/open-quantum-control`
  - Related, but different focus.
  - This is the open-quantum-control/NMR/control/reproduction line.
  - Use it only when the task is explicitly about control, tomography, noise spectroscopy, or the review article in that repository.

- `repos/Fiscomp`
  - Support/teaching/numerical material.
  - Not the source of truth for the transport lab.

- `repos/Assyntrax`
  - Umbrella workspace/application repository.
  - Not the source of truth for transport science outputs.

## Rule for multi-repo work

If the task is about:

- transport in graphs/media/open quantum systems:
  - start in `Quantum-systems`.
- NMR/open quantum control/tomography/control review:
  - start in `open-quantum-control`.
- generic classroom/numerical exercises:
  - start in `Fiscomp`.

Do not spread transport-lab state across multiple repositories. Keep the scientific state in `Quantum-systems`.
