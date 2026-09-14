"""
generate_map.py

Standalone script (NOT a ROS 2 node) that produces a Nav2-compatible
occupancy grid map (map.pgm + map.yaml) matching the known, static
geometry already defined in agri_field.sdf.

This is a deliberate simulation simplification: rather than running
SLAM to discover the environment, we already know the exact geometry
(it's our own Gazebo world), so we encode that ground truth directly
into a map. This is explicitly labeled as a simplification, not a
substitute for real mapping/SLAM.

Run once, offline:
    python3 generate_map.py

Produces map.pgm and map.yaml in the current directory.
"""

import numpy as np
from PIL import Image

# --- Map configuration ---
resolution = 0.05  # meters per pixel/cell

# Matches the boundary walls in agri_field.sdf (walls at x=+-6, y=+-6)
world_min_x, world_max_x = -6.0, 6.0
world_min_y, world_max_y = -6.0, 6.0

# --- Grid dimensions ---
# Pixels = meters / resolution. With a 12m field at 0.05m/px, this
# gives 240x240 pixels.
width_px = int(round((world_max_x - world_min_x) / resolution))
height_px = int(round((world_max_y - world_min_y) / resolution))

# Start entirely free (254 = free space, per Nav2/ROS map convention).
# 0 = occupied, 205 = unknown (unused here since we know the whole
# environment already).
grid = np.full((height_px, width_px), 254, dtype=np.uint8)

# --- Known obstacles, taken directly from agri_field.sdf ---
# Each entry: (center_x, center_y, size_x, size_y)
# Wall sizes are given in world (x, y) extent, already accounting for
# the 90-degree yaw rotation on the east/west walls (so their size_x
# and size_y are swapped relative to how they're written in the SDF,
# which specifies box dimensions BEFORE rotation).
obstacles = [
    (2.0, 0.0, 1.0, 1.0),      # obstacle_1
    (2.0, -1.3, 1.0, 1.0),     # obstacle_2
    (0.0, 6.0, 12.0, 0.2),     # boundary_wall_north
    (0.0, -6.0, 12.0, 0.2),    # boundary_wall_south
    (6.0, 0.0, 0.2, 12.0),     # boundary_wall_east  (rotated 90deg)
    (-6.0, 0.0, 0.2, 12.0),    # boundary_wall_west  (rotated 90deg)
]


def world_to_pixel(x, y):
    """
    Convert a world (x, y) coordinate to a (col, row) pixel index.

    The map's origin (world_min_x, world_min_y) corresponds to the
    BOTTOM-LEFT of the map, per standard ROS map convention (Y
    increases upward in the world). PGM files store rows top-to-bottom,
    so row 0 in the file is the HIGHEST world Y, not the lowest --
    this is why the row calculation is flipped relative to the column
    calculation.
    """
    col = (x - world_min_x) / resolution
    row = height_px - 1 - (y - world_min_y) / resolution
    return col, row


for (cx, cy, sx, sy) in obstacles:
    # Compute the obstacle's world-space bounding box corners.
    x_min = cx - sx / 2.0
    x_max = cx + sx / 2.0
    y_min = cy - sy / 2.0
    y_max = cy + sy / 2.0

    # Convert all four corners to pixel space. Because the row axis is
    # flipped (increasing world Y -> decreasing row), the world y_max
    # corner produces the SMALLER row index, and y_min produces the
    # LARGER row index. We resolve this with min()/max() rather than
    # assuming a fixed order, so the slicing below is always correct
    # regardless of the flip.
    col_a, row_a = world_to_pixel(x_min, y_min)
    col_b, row_b = world_to_pixel(x_max, y_max)

    col_start = int(round(min(col_a, col_b)))
    col_end = int(round(max(col_a, col_b)))
    row_start = int(round(min(row_a, row_b)))
    row_end = int(round(max(row_a, row_b)))

    # Clip to grid bounds in case any obstacle edge falls exactly on
    # or outside the map boundary.
    col_start = max(0, col_start)
    row_start = max(0, row_start)
    col_end = min(width_px, col_end)
    row_end = min(height_px, row_end)

    # Mark this region occupied (0 = black).
    grid[row_start:row_end, col_start:col_end] = 0

# --- Write the image ---
img = Image.fromarray(grid, mode='L')
img.save('map.pgm')

# --- Write the companion metadata file ---
with open('map.yaml', 'w') as f:
    f.write(
        "image: map.pgm\n"
        f"resolution: {resolution}\n"
        f"origin: [{world_min_x}, {world_min_y}, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.196\n"
    )

print(f"Map generated: {width_px}x{height_px} pixels at {resolution} m/px")
print(f"World bounds: x[{world_min_x}, {world_max_x}]  y[{world_min_y}, {world_max_y}]")
print("Wrote map.pgm and map.yaml")