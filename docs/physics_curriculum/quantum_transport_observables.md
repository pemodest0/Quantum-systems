# Quantum Transport Observables

Goal: know exactly what each number in the campaign tables means.

## Target arrival

```text
eta(T) = population accumulated in the target channel at final time T
```

Plain meaning: fraction of the initial excitation that successfully reached the desired output.

This is the primary success metric.

## Population dynamics

```text
p_i(t) = rho_ii(t)
```

Plain meaning: how much excitation is on each site at time `t`.

Population dynamics tells whether amplitude oscillates, spreads, localizes, or drains quickly.

## Coherence

A common coherence measure is

```text
C_l1(t) = sum_{i != j} |rho_ij(t)|
```

Plain meaning: how much phase relation remains between different sites.

Coherence is not automatically good or bad. It depends on whether interference helps the target or traps population elsewhere.

## Mean position

If each site has a coordinate `x_i`, then

```text
<x>(t) = sum_i p_i(t) x_i
```

It tells where the center of population is.

## Mean squared displacement

```text
MSD(t) = sum_i p_i(t) |x_i - x_initial|^2
```

It measures spreading away from the initial site.

## Front width

Front width is the square root of the spatial variance:

```text
width(t) = sqrt(<x^2> - <x>^2)
```

In 2D, the same idea uses vector coordinates.

## First hitting time

First hitting time is the first time where target arrival crosses a threshold:

```text
eta(t) >= eta_threshold
```

If the threshold is never crossed, report "not reached" instead of inventing a time.

## Interface crossing

For a chosen cut through the medium, integrated crossing estimates how much population has moved from one side to another. This is useful for bottlenecks and 2D media, but it is not the same as target arrival.

Common mistake: comparing observables computed on different normalizations. Always state whether the result is full-state, graph-only normalized, or target-inclusive.

