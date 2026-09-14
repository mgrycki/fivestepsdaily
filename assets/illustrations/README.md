# Illustration library

Generated once in Midjourney, committed here, picked per post by name. No API, no per-post cost.

## How to generate

1. Open https://www.midjourney.com/imagine
2. Run the **style anchor** prompt first. Pick the cleanest of the four, open it, copy its image URL.
3. Every other prompt below gets `--sref <that URL>` appended, so the whole set shares one look.
4. Save each accepted image as `assets/illustrations/<name>.png` (or `.jpg`), 1:1, at least 1024 px.
5. Commit and push. `python -c "from src import generate; print(generate.ILLUSTRATIONS)"` lists what the
   pipeline can see.

Common parameters for every prompt (Midjourney v7):

```
--ar 1:1 --style raw --stylize 50 --v 7
```

Style anchor (run this once, then use its URL as --sref):

```
flat vector editorial illustration, modern infographic style, bold simple geometric shapes,
thick clean outlines, confident flat colour fills, soft depth by overlapping shapes only,
limited palette of sky blue and warm orange on plain white background, centred single
subject, generous margin, no text, no letters, no numbers, no logos
--ar 1:1 --style raw --stylize 50 --v 7
```

Keep the subject on **plain white**. The frame places the image on a white card, so there is
nothing to cut out. Do not ask for transparency, MJ does not produce it.

## Subjects (file name -> prompt subject)

Prefix each with the style anchor text, append `--sref <URL>` and the common parameters.

| file | subject |
|---|---|
| `bioreactor` | a stainless steel laboratory bioreactor vessel with coiled tubing and floating molecule shapes |
| `dna-helix` | a DNA double helix with a few base pairs highlighted |
| `microscope` | a modern lab microscope with a glowing sample slide |
| `vaccine-vial` | a glass vaccine vial next to a syringe |
| `pill-capsule` | an oversized medicine capsule splitting open with particles |
| `human-heart` | a stylised human heart with circulation arrows |
| `brain-neurons` | a stylised brain with glowing neural pathways |
| `virus-particle` | a spiky virus particle with a shield fragment |
| `plant-seedling` | a seedling breaking through soil with roots visible |
| `atom-model` | an atom with orbiting electrons |
| `molecule-lattice` | a crystal lattice of connected molecules |
| `water-treatment` | a water droplet passing through filter layers |
| `flame-reactor` | a furnace with a controlled flame and heat waves |
| `solar-panel` | a tilted solar panel under a bright sun |
| `wind-turbine` | a wind turbine on a hill with motion arcs |
| `battery-cell` | a cutaway lithium battery cell with layers |
| `power-grid` | a transmission tower with power lines and a lightning bolt |
| `microchip` | a microchip with visible traces, seen slightly from above |
| `server-rack` | a server rack with glowing status lights |
| `data-flow` | abstract data streams flowing through a funnel |
| `cloud-network` | a cloud connected to several devices by lines |
| `code-terminal` | a laptop screen with abstract code blocks |
| `neural-network` | a layered neural network diagram with connected nodes |
| `robot-arm` | an industrial robot arm placing a component |
| `satellite-orbit` | a satellite orbiting a planet with a signal arc |
| `rocket-launch` | a rocket lifting off with a plume of smoke |
| `telescope-sky` | a telescope pointed at a starry sky |
| `gear-mechanism` | interlocking gears in motion |
| `factory-line` | a factory conveyor belt with boxes |
| `cargo-truck` | a delivery truck on a road with a route line |
| `container-ship` | a container ship with stacked containers |
| `airplane-flight` | an airplane in flight with a dotted trajectory |
| `warehouse-boxes` | a warehouse aisle with shelves of boxes |
| `laser-beam` | a laser device emitting a focused beam onto a surface |
| `3d-printer` | a 3D printer mid-print with a half-built object |
| `sensor-waves` | a small sensor emitting concentric waves |
| `camera-lens` | a camera lens with light rays entering |
| `chemistry-flasks` | three lab flasks with coloured liquids and bubbles |
| `heat-exchange` | pipes carrying hot and cold flows side by side |
| `freezer-cold` | a cold storage unit with frost and snowflakes |
| `recycling-loop` | materials moving around a recycling loop |
| `globe-map` | a globe with connection lines between cities |
| `shield-lock` | a shield with a padlock, security concept |
| `chart-growth` | a rising bar chart with an arrow |
| `people-team` | three abstract people figures collaborating |
| `document-stack` | a stack of documents with a magnifying glass |
| `clock-timeline` | a clock face merged with a timeline |
| `target-arrow` | an arrow hitting the centre of a target |

Add more any time: drop a file in, the name becomes selectable on the next run.
