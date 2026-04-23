# Environment-Assisted Transport

Goal: understand when noise can help and when it hurts.

## Basic idea

Coherent quantum motion can be fast, but it can also create destructive interference. Disorder can also localize the excitation. Moderate phase scrambling can sometimes break harmful interference or help escape localization.

This is environment-assisted transport.

## Minimal expected pattern

As phase scrambling increases:

1. Very low phase scrambling: coherent oscillations or localization may limit target arrival.
2. Moderate phase scrambling: target arrival can improve.
3. Very high phase scrambling: motion can be suppressed because the environment interrupts transfer too often.

The high-noise suppression is often called Zeno-like behavior.

## What counts as useful assistance in this lab

Use the lab thresholds:

- `gain < 0.02`: no meaningful assistance.
- `0.02 <= gain < 0.05`: weak effect.
- `gain >= 0.05`: clear effect.

Call it strong only when:

- gain is at least `0.05`.
- best phase scrambling is nonzero.
- the pattern persists across at least two adjacent disorder values.
- ensemble spread does not erase the separation.

## Disorder and phase scrambling

Disorder strength `W/J` says how uneven the site energies are compared with hopping.

Phase scrambling `gamma_phi/J` says how strongly the environment randomizes phases compared with hopping.

The interesting region is often neither perfectly coherent nor fully classical. It is the crossover where interference, disorder, and noise compete.

## Relation to ring target placement

In a ring, target placement can change whether coherent paths interfere constructively or destructively. A favorable target may already work well without noise. An unfavorable target may benefit more from phase scrambling if noise breaks harmful interference.

Common mistake: "noise helped in one parameter point, therefore noise is good." Correct reading: assistance is a window in parameter space, not a universal rule.

