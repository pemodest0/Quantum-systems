# How to Read Lab Figures

Goal: read each plot slowly and avoid false conclusions.

## Heatmap

A heatmap shows a measured number as color.

Typical axes:

- horizontal axis: phase scrambling compared with hopping, `gamma_phi/J`.
- vertical axis: disorder compared with hopping, `W/J`.
- color: target arrival, spreading, coherence, or regime label.

Read it by asking:

- Which color means high?
- Where is the best region?
- Is the best region a single pixel or a stable area?
- Does ensemble spread make the difference uncertain?

## Dashboard

A dashboard usually compares summary numbers:

- zero-scrambling arrival: success when environment phase scrambling is off.
- best arrival: highest success found in the scan.
- gain: best arrival minus zero-scrambling arrival.
- best phase scrambling: value where the best arrival occurred.
- ensemble spread: uncertainty across disorder seeds.

## 3D surface

A 3D surface shows the same map as a landscape. Peaks are high values. Valleys are low values.

Use it for intuition, not for precise claims. The heatmap and tables are better for exact numbers.

## Animation

An animation shows population moving through the medium in time.

Read it as:

- bright site: high local population.
- target marker: desired arrival site.
- fading or shrinking total brightness: population leaving graph into target or loss channels.

Animation is for mechanism intuition. The final claim still comes from measured observables.

## Figure explanation checklist

For every main figure, the assistant must say:

- what the title means.
- what each axis means.
- what each color, curve, or marker means.
- what literature would expect.
- what the lab measured.
- whether the effect is strong, weak, or inconclusive.
- what remains uncertain.

Common mistake: trusting a visually pretty plot. Scientific strength comes from stable metrics, controls, and uncertainty.

