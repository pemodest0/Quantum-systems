# Physics Curriculum for the Local Assistant

This folder is the didactic base used by the local physics assistant. It is not a fine-tuning dataset. It is a local, citable curriculum for retrieval-augmented generation.

Policy for the assistant:

- If an answer is not supported by a local curriculum module, a paper card, a campaign result, or an explicit calculation, the assistant must say that the current base is insufficient.
- The assistant may explain in PT-BR, but it must keep technical terms in English when those terms are used in code or figures.
- Transport success and spatial spreading are different concepts. The assistant must not treat a wider wave packet as proof of better arrival at the target.
- Pilot ensembles are not definitive evidence. Strong claims require enough seeds, a stable parameter region, and consistency with the literature guardrails.

Core notation:

- `i, j`: site indices.
- `N`: number of sites.
- `|i>`: local basis state with one excitation on site `i`.
- `epsilon_i`: local site energy.
- `J_ij`: coherent coupling between sites `i` and `j`.
- `W/J`: disorder strength compared with coherent coupling.
- `gamma_phi/J`: phase scrambling rate compared with coherent coupling.
- `kappa/J`: successful arrival rate into the target channel.
- `Gamma/J`: loss rate to uncontrolled channels.
- `eta(T)`: accumulated target arrival at the final time.
- `rho(t)`: density matrix at time `t`.

