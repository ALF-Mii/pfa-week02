"""
Chandelier Generator for Maya (Route B - new tool)

Design problem: Environment/lighting artists need a fast placeholder
chandelier that still reads as a chandelier from a distance - central stem,
radiating arms, candles/bulbs - without modeling it by hand. It has to get
right: (1) proportions stay sane as arm count changes, (2) clean hierarchy
for art direction, (3) safe to undo/delete in someone else's scene.

New capabilities vs a single static prop:
- Two kinds: round (radial) and square (cube-frame) styles
- Many where it did one: N arms x M tiers, parametric
- Handled input: clamps/corrects bad UI or script input on purpose

Habits:
- Undo in one step via openChunk/closeChunk
- Delete only what it made via group + registry (no wildcard deletes)
"""
import math

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

# Registry of groups THIS tool created (for safe delete)
CREATED_GROUPS = []
_CHANDELIER_PREFIX = "chandelier_"
_counter = 0


def _require_maya():
    if cmds is None:
        raise RuntimeError("This script must run inside Maya (maya.cmds not found).")


def _sanitize_inputs(num_arms, radius, height, tiers, style):
    """Handle inputs you didn't plan for - on purpose."""
    # num_arms: int 3..12
    try:
        num_arms = int(num_arms)
    except (TypeError, ValueError):
        num_arms = 6
    num_arms = max(3, min(12, num_arms))

    # radius / height: positive floats with sane caps
    try:
        radius = float(radius)
    except (TypeError, ValueError):
        radius = 5.0
    try:
        height = float(height)
    except (TypeError, ValueError):
        height = 8.0
    if not (0.5 <= radius <= 20.0):
        radius = 5.0
    if not (1.0 <= height <= 30.0):
        height = 8.0

    # tiers: 1 or 2 only
    try:
        tiers = int(tiers)
    except (TypeError, ValueError):
        tiers = 1
    tiers = 2 if tiers >= 2 else 1

    # style: 'round' or 'square', default round
    if style not in ("round", "square"):
        style = "round"

    return num_arms, radius, height, tiers, style


def _unique_name(style):
    global _counter
    _counter += 1
    return "{}{}_{}".format(_CHANDELIER_PREFIX, style, _counter)


def _make_part(make_fn, *args, **kwargs):
    """Create one primitive, return its transform node."""
    nodes = make_fn(*args, **kwargs)
    # poly* commands return [transform, history]; we want transform
    if isinstance(nodes, (list, tuple)):
        return nodes[0]
    return nodes


def _build_tier(parent_group, num_arms, radius, y, style, tier_scale=1.0):
    """Build one tier of arms. Returns list of nodes (already parented)."""
    r = radius * tier_scale
    parts = []

    if style == "round":
        # Round support ring: torus so dishes/candles stand on something,
        # matching the square style's cube-beam frame.
        ring = _make_part(
            cmds.polyTorus, r=r, sr=0.12 * tier_scale, name="ring_tmp"
        )
        cmds.move(0, y, 0, ring)
        cmds.parent(ring, parent_group)
        parts.append(ring)

    if style == "square":
        # Square frame: 4 thin cubes forming a square of side r
        side = r * 1.4
        beam_h = 0.15
        for rot_y, pos in [
            (0, (0, y, side / 2)),
            (0, (0, y, -side / 2)),
            (90, (side / 2, y, 0)),
            (90, (-side / 2, y, 0)),
        ]:
            beam = _make_part(
                cmds.polyCube, w=side, h=beam_h, d=beam_h, name="beam_tmp"
            )
            cmds.move(pos[0], pos[1], pos[2], beam)
            if rot_y:
                cmds.rotate(0, rot_y, 0, beam)
            cmds.parent(beam, parent_group)
            parts.append(beam)

    for i in range(num_arms):
        if style == "round":
            angle = (2.0 * math.pi * i) / num_arms
            x = math.cos(angle) * r
            z = math.sin(angle) * r
            rot_y = -math.degrees(angle)
        else:
            # Square: distribute arms evenly around the square perimeter
            t = float(i) / num_arms * 4.0  # 0..4
            side_idx = int(t) % 4
            frac = (t % 1.0) - 0.5  # -0.5..0.5 along side
            side = r * 1.4
            if side_idx == 0:
                x, z, rot_y = frac * side, side / 2, 0
            elif side_idx == 1:
                x, z, rot_y = frac * side, -side / 2, 0
            elif side_idx == 2:
                x, z, rot_y = side / 2, frac * side, 90
            else:
                x, z, rot_y = -side / 2, frac * side, 90

        # Horizontal arm: thin cylinder from center to (x, z)
        arm_len = math.sqrt(x * x + z * z)
        arm = _make_part(
            cmds.polyCylinder,
            r=0.08 * tier_scale,
            h=arm_len,
            sz=8,
            name="arm_tmp",
        )
        # Cylinder axis is Y; rotate to lie flat pointing outward
        cmds.rotate(0, 0, 90, arm)
        cmds.rotate(0, rot_y, 0, arm)
        cmds.move(x / 2.0, y, z / 2.0, arm)
        cmds.parent(arm, parent_group)
        parts.append(arm)

        # Candle holder dish: short wide cylinder
        dish = _make_part(
            cmds.polyCylinder, r=0.28 * tier_scale, h=0.08, sz=12, name="dish_tmp"
        )
        cmds.move(x, y + 0.1, z, dish)
        cmds.parent(dish, parent_group)
        parts.append(dish)

        # Candle stick: thin tall cylinder
        candle = _make_part(
            cmds.polyCylinder, r=0.12 * tier_scale, h=0.9, sz=8, name="candle_tmp"
        )
        cmds.move(x, y + 0.55, z, candle)
        cmds.parent(candle, parent_group)
        parts.append(candle)

        # Bulb / flame: sphere
        bulb = _make_part(
            cmds.polySphere, r=0.18 * tier_scale, sx=10, sy=8, name="bulb_tmp"
        )
        cmds.move(x, y + 1.15, z, bulb)
        cmds.parent(bulb, parent_group)
        parts.append(bulb)

        # Joint cube: small decorative cube where arm meets ring
        joint = _make_part(
            cmds.polyCube,
            w=0.22 * tier_scale,
            h=0.22 * tier_scale,
            d=0.22 * tier_scale,
            name="joint_tmp",
        )
        cmds.move(x * 0.55, y, z * 0.55, joint)
        cmds.parent(joint, parent_group)
        parts.append(joint)

    return parts


def build_chandelier(num_arms=6, radius=5.0, height=8.0, tiers=1, style="round"):
    """
    Build a chandelier from primitives. All geometry is parented under
    one group so delete is safe. Undo is one chunk.

    Returns the group name.
    """
    _require_maya()
    num_arms, radius, height, tiers, style = _sanitize_inputs(
        num_arms, radius, height, tiers, style
    )

    group_name = _unique_name(style)

    cmds.undoInfo(openChunk=True)
    try:
        grp = cmds.group(empty=True, name=group_name)

        # Ceiling mount: flat cylinder at top
        mount = _make_part(cmds.polyCylinder, r=0.6, h=0.3, sz=16, name="mount_tmp")
        cmds.move(0, height, 0, mount)
        cmds.parent(mount, grp)

        # Stem: long thin cylinder
        stem = _make_part(cmds.polyCylinder, r=0.12, h=height, sz=10, name="stem_tmp")
        cmds.move(0, height / 2.0, 0, stem)
        cmds.parent(stem, grp)

        # Central column decoration: stacked spheres + short cylinders
        for j, (sy, sr) in enumerate([(height * 0.55, 0.5), (height * 0.35, 0.35)]):
            ball = _make_part(cmds.polySphere, r=sr, sx=14, sy=10, name="core_tmp")
            cmds.move(0, sy, 0, ball)
            cmds.parent(ball, grp)
            collar = _make_part(
                cmds.polyCylinder, r=sr * 0.5, h=0.25, sz=12, name="collar_tmp"
            )
            cmds.move(0, sy + sr + 0.1, 0, collar)
            cmds.parent(collar, grp)

        # Tier(s)
        _build_tier(grp, num_arms, radius, height * 0.45, style, tier_scale=1.0)
        if tiers == 2:
            _build_tier(grp, num_arms, radius, height * 0.65, style, tier_scale=0.65)

        # Bottom finial: sphere
        finial = _make_part(cmds.polySphere, r=0.4, sx=12, sy=8, name="finial_tmp")
        cmds.move(0, height * 0.45 - 0.8, 0, finial)
        cmds.parent(finial, grp)

        CREATED_GROUPS.append(grp)
        return grp
    finally:
        cmds.undoInfo(closeChunk=True)


def delete_chandelier(group_name):
    """Delete ONLY the group this tool made. Never wildcard-delete."""
    _require_maya()
    if group_name not in CREATED_GROUPS:
        # Also allow prefix match only if we created it this session;
        # otherwise refuse - protects tree_oak_final-type accidents.
        raise ValueError(
            "Refusing to delete '{}': not created by this tool.".format(group_name)
        )
    if cmds.objExists(group_name):
        cmds.delete(group_name)
    CREATED_GROUPS.remove(group_name)


def delete_last_chandelier():
    """Delete the most recently created chandelier."""
    _require_maya()
    if not CREATED_GROUPS:
        cmds.warning("No chandeliers created by this tool to delete.")
        return
    delete_chandelier(CREATED_GROUPS[-1])


def show_ui():
    """Simple control window."""
    _require_maya()
    win = "chandelierWin"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)
    cmds.window(win, title="Chandelier Generator")
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.intSliderGrp("armsSlider", label="Arms", min=3, max=12, value=6, field=True)
    cmds.floatSliderGrp(
        "radiusSlider", label="Radius", min=1.0, max=15.0, value=5.0, field=True
    )
    cmds.floatSliderGrp(
        "heightSlider", label="Height", min=2.0, max=20.0, value=8.0, field=True
    )
    cmds.intSliderGrp("tiersSlider", label="Tiers", min=1, max=2, value=1, field=True)
    cmds.optionMenuGrp("styleMenu", label="Style")
    cmds.menuItem(label="round")
    cmds.menuItem(label="square")
    cmds.button(
        label="Build Chandelier",
        command=lambda *_: build_chandelier(
            cmds.intSliderGrp("armsSlider", q=True, value=True),
            cmds.floatSliderGrp("radiusSlider", q=True, value=True),
            cmds.floatSliderGrp("heightSlider", q=True, value=True),
            cmds.intSliderGrp("tiersSlider", q=True, value=True),
            cmds.optionMenuGrp("styleMenu", q=True, value=True),
        ),
    )
    cmds.button(label="Undo Last (Delete)", command=lambda *_: delete_last_chandelier())
    cmds.showWindow(win)


# Run UI when executed inside Maya; otherwise no-op with a clear message.
if __name__ == "__main__" and cmds is not None:
    show_ui()
