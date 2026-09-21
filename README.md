# pfa-week02
Week 2 programming for animators homework assingment.

## What it does now (Route B level-up)

Chandelier Generator builds parametric placeholder chandeliers for env/lighting blockouts — a problem I kept hitting where hand-modeling each fixture killed pacing. I solved it with one tool covering two styles (round torus-ring and square cube-frame) that scales cleanly: 1–5 tiers, 3–12 arms, filler lights on the support plus an inner center ring with its own height/spread controls, and three art-directable materials (metal / trim hardware / glowing lights with brightness).

## What does not work

Ran into an issue with the textures, where the glowing lights wont apply to the correct objects on the chandelier. I tried to fix this with the OpenCode agent but I kept running into the same issue anyways. 

## Video Recording

https://drive.google.com/file/d/13hxqjkrXyUS6oZyGlKJaTIYT9AQoF2MX/view?usp=sharing

## How to run (Maya 2022+)

1. Put `chandelier_generator.py` anywhere, e.g. `Documents/maya/scripts`.
2. In Maya Script Editor (Python tab):
```python
import sys
sys.path.append(r"C:/Users/alfre/Documents/Default Project")
import chandelier_generator as cg
cg.show_ui()
