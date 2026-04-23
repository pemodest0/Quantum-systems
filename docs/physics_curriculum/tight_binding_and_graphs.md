# Tight Binding and Graphs

Goal: connect the graph picture with the Hamiltonian used in the simulation.

## Sites

Each node of a graph is a local quantum site. It can represent a chromophore, a qubit, a local mode, or an effective position in a medium.

The local basis is

```text
{|0>, |1>, ..., |N-1>}
```

where `|i>` means "one excitation localized at site `i>`".

## Edges

An edge between sites `i` and `j` means coherent transfer is allowed between them. The strength of that transfer is `J_ij`.

If two sites are connected, the Hamiltonian contains

```text
J_ij |i><j| + J_ji |j><i|
```

For a real symmetric network, `J_ij = J_ji`.

## Tight-binding Hamiltonian

The minimal Hamiltonian is

```text
H = sum_i epsilon_i |i><i| + sum_{i != j} J_ij |i><j|
```

Meaning:

- `epsilon_i`: local energy of site `i`.
- `J_ij`: coherent hopping strength between `i` and `j`.
- diagonal terms decide how phase rotates locally.
- off-diagonal terms move amplitude between sites.

## Disorder

Disorder means the local energies are not all equal:

```text
epsilon_i = random value in a range controlled by W
```

In the lab, `W/J` means "how large the disorder is compared with the normal hopping strength". Large `W/J` can localize the excitation and reduce target arrival.

## Geometry-aware media

In a pure graph, an edge is just a connection. In a physical medium, each site also has coordinates. Then couplings may depend on distance:

```text
nearest neighbor: J_ij = J if sites touch
exponential:      J_ij = J exp(-r_ij / xi)
power law:        J_ij = J / r_ij^alpha
```

Coordinates let the lab measure spreading, front width, and mean squared displacement.

Common mistake: saying a complete graph must transport best because it has many links. Symmetry can create dark or poorly coupled subspaces, so connectivity alone is not a reliable predictor.

