
import os
import re
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString


# Main admin settings file
CONC_PATH = "conc.yaml"
# Camera zones file
CONFIG_PATH = "config.yaml"

yaml_ruamel = YAML()
yaml_ruamel.preserve_quotes = True
yaml_ruamel.width = 4096
yaml_ruamel.indent(sequence=4, offset=2)


# ---------------- YAML HELPERS ----------------
def load_yaml_preserve(path=CONC_PATH):
    """Load YAML with ruamel (for reading only)."""
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml_ruamel.load(f)
    return {}


# 🚩 Scalar updater
def update_yaml_value(key, new_value, path=CONC_PATH):
    """
    Update a scalar value in YAML while preserving inline comments.
    Supports dotted keys like 'background_p0.threshold'.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r") as f:
        lines = f.readlines()

    parts = key.split(".")
    if len(parts) == 1:
        parent = None
        target_key = parts[0]
    else:
        parent, target_key = parts

    # Build regex for "key: value  # comment"
    pattern = re.compile(rf"^(\s*{re.escape(target_key)}\s*:\s*)([^\n#]*)(.*)$")

    start, end = 0, len(lines)
    if parent:
        parent_pattern = re.compile(rf"^\s*{re.escape(parent)}\s*:")
        for i, line in enumerate(lines):
            if parent_pattern.match(line):
                start = i
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(" "):
                        end = j
                        break
                if end is None:
                    end = len(lines)
                break
        else:
            raise KeyError(f"Parent key '{parent}' not found")

    # Update inside block
    updated_block, replaced = [], False
    for line in lines[start:end]:
        match = pattern.match(line)
        if match:
            prefix, _old_val, comment = match.groups()
            comment = comment.rstrip("\n")
            if comment and not comment.startswith(" "):
                comment = " " + comment   # 👈 ensure one space before comment
            updated_block.append(f"{prefix}{new_value}{comment}\n")  # 👈 KEY UPDATE
            replaced = True
        else:
            updated_block.append(line)


    if not replaced:
        raise KeyError(f"Key '{target_key}' not found in YAML file")

    lines[start:end] = updated_block

    with open(path, "w") as f:
        f.writelines(lines)


# 🚩 List updater
def update_yaml_list(key, new_list, path=CONC_PATH):
    """
    Update a list in YAML while preserving inline comments if present.
    Example:
      points:
        - [640, 480]  # red_left_bottom
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r") as f:
        lines = f.readlines()

    # Locate block
    start, end = None, None
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}:"):
            start = i
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and not lines[j].startswith(" "):
                    end = j
                    break
            if end is None:
                end = len(lines)
            break

    if start is None:
        raise KeyError(f"Key '{key}' not found in YAML file")

    # Indentation
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    indent = " " * (base_indent + 2)

    # --- Patch block ---
    block = lines[start:end]
    new_block = [block[0]]  # keep "key:" line
    item_idx = 0
    inside_items = False

    for line in block[1:]:
        if line.strip().startswith("-"):
            inside_items = True
            if item_idx < len(new_list):
                # Replace only the value inside brackets/after dash, keep comments
                if isinstance(new_list[item_idx], (list, tuple)):
                    new_val = f"[{new_list[item_idx][0]}, {new_list[item_idx][1]}]"
                else:
                    new_val = str(new_list[item_idx])

                updated_line = re.sub(
                    r"(-\s*)(\[.*?\]|\S+)(.*)$",
                    rf"\1{new_val}\3",
                    line
                )
                new_block.append(updated_line if updated_line.endswith("\n") else updated_line + "\n")
                item_idx += 1
            else:
                # drop extra old items
                continue
        else:
            new_block.append(line)

    # Add extra new items if needed
    if item_idx < len(new_list):
        for item in new_list[item_idx:]:
            if isinstance(item, (list, tuple)):
                new_block.insert(-1, f"{indent}- [{item[0]}, {item[1]}]\n")
            else:
                new_block.insert(-1, f"{indent}- {item}\n")

    lines[start:end] = new_block

    with open(path, "w") as f:
        f.writelines(lines)


# 🚩 Smart updater
def update_yaml(key, value, path=CONC_PATH):
    if isinstance(value, (list, tuple)):
        update_yaml_list(key, value, path)
    else:
        update_yaml_value(key, value, path)


# ---------------- CAMERA HELPERS ----------------
# def update_config_for_camera(cam_index):
#     """
#     Update config.yaml with cam_id and RTSP URL from conc.yaml.
#     """
#     yaml = YAML()
#     yaml.preserve_quotes = True
#     yaml.width = 4096
#     yaml.indent(sequence=4, offset=2)

#     # --- Load config.yaml ---
#     with open("config.yaml", "r") as f:
#         cfg = yaml.load(f)

#     # --- Load conc.yaml ---
#     with open("conc.yaml", "r") as f:
#         conc = yaml.load(f)

#     # ✅ Update cam_id
#     cfg["cam_id"] = cam_index

#     # ✅ Build full RTSP URL with enforced double quotes
#     cam_key = f"background_p{cam_index}"
#     if cam_key in conc:
#         ip_path = conc[cam_key].get("ip_address")
#         if ip_path:
#             rtsp_prefix = "rtsp://admin:Cogn!@2023@"
#             cfg["camera_pos"] = DoubleQuotedScalarString(rtsp_prefix + ip_path)

#     # --- Save config.yaml back (preserve formatting & comments) ---
#     with open("config.yaml", "w") as f:
#         yaml.dump(cfg, f)
def update_config_for_camera(cam_index):
    """
    Update config.yaml with cam_id and camera_pos
    using the numeric mapping for M-series.
    """
    CAMERA_POS_MAP = {0: 0, 1: 2, 2: 4, 3: 6}
    CAM_ID_MAP     = {0: 0, 1: 1, 2: 2, 3: 3}

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(sequence=4, offset=2)

    # --- Load config.yaml ---
    with open("config.yaml", "r") as f:
        cfg = yaml.load(f)

    # ✅ Apply numeric mapping
    if cam_index in CAMERA_POS_MAP:
        cfg["camera_pos"] = CAMERA_POS_MAP[cam_index]
    if cam_index in CAM_ID_MAP:
        cfg["cam_id"] = CAM_ID_MAP[cam_index]

    # --- Save config.yaml ---
    with open("config.yaml", "w") as f:
        yaml.dump(cfg, f)


# def save_points_to_config(cam_index, points):
#     """
#     Save clicked zone points into config.yaml (structured)
#     and patch conc.yaml (line-preserving).
#     """
#     yaml = YAML()
#     yaml.preserve_quotes = True
#     yaml.width = 4096
#     yaml.indent(sequence=4, offset=2)

#     key = f"p{cam_index}_zone_coords"

#     # ---------------- CONFIG.YAML (dump is OK) ----------------
#     with open("config.yaml", "r") as f:
#         cfg = yaml.load(f)

#     if key not in cfg:
#         cfg[key] = {
#             "red": [],
#             "orange": [],
#             "blue": [],
#             "line_thickness": 2,
#             "num_zones": 1
#         }

#     red_points = []
#     for pt in points:
#         seq = CommentedSeq(pt)
#         seq.fa.set_flow_style()
#         red_points.append(seq)

#     cfg[key]["red"] = red_points
#     cfg[key]["orange"] = []
#     cfg[key]["blue"] = []
#     cfg[key]["num_zones"] = 1
#     cfg[key]["line_thickness"] = 2

#     with open("config.yaml", "w") as f:
#         yaml.dump(cfg, f)
# def save_points_to_config(cam_index, zone_color, points):
#     yaml = YAML()
#     yaml.preserve_quotes = True
#     yaml.width = 4096
#     yaml.indent(sequence=4, offset=2)

#     key = f"p{cam_index}_zone_coords"

#     with open("config.yaml", "r") as f:
#         cfg = yaml.load(f)

#     if key not in cfg:
#         cfg[key] = {
#             "red": [],
#             "orange": [],
#             "blue": [],
#             "line_thickness": 2,
#             "num_zones": 1
#         }

#     formatted_points = []
#     for pt in points:
#         seq = CommentedSeq(pt)
#         seq.fa.set_flow_style()
#         formatted_points.append(seq)

#     cfg[key][zone_color] = formatted_points
#     cfg[key]["num_zones"] = max(
#         cfg[key].get("num_zones", 1),
#         1 if cfg[key]["red"] else 0 + 1 if cfg[key]["orange"] else 0 + 1 if cfg[key]["blue"] else 0
#     )
#     cfg[key]["line_thickness"] = 2

#     with open("config.yaml", "w") as f:
#         yaml.dump(cfg, f)
def save_points_to_config(cam_index, zone_color, points):
    """
    Save clicked zone points into config.yaml for the given camera & color.
    Other colors remain untouched.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(sequence=4, offset=2)

    key = f"p{cam_index}_zone_coords"

    with open("config.yaml", "r") as f:
        cfg = yaml.load(f)

    # Ensure structure exists
    if key not in cfg:
        cfg[key] = {"red": [], "orange": [], "blue": [], "line_thickness": 2, "num_zones": 1}

    # Format new points
    new_points = []
    for pt in points:
        seq = CommentedSeq(pt)
        seq.fa.set_flow_style()
        new_points.append(seq)

    # ✅ Update only the chosen color
    cfg[key][zone_color] = new_points

    # ✅ Preserve thickness
    if "line_thickness" not in cfg[key]:
        cfg[key]["line_thickness"] = 2

    # ✅ Recompute num_zones
    cfg[key]["num_zones"] = sum(1 for z in ["red", "orange", "blue"] if cfg[key][z])

    with open("config.yaml", "w") as f:
        yaml.dump(cfg, f)


def save_points_to_conc(cam_index, zone_color, points):
    """
    Line-preserving update for conc.yaml.
    Updates only the given camera's zone_color list.
    """
    key = f"p{cam_index}_zone_coords"

    with open("conc.yaml", "r") as f:
        lines = f.readlines()

    # locate section
    section = f"{key}:"
    start, end = None, None
    for i, line in enumerate(lines):
        if line.strip().startswith(section):
            start = i
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and not lines[j].startswith(" "):
                    end = j
                    break
            if end is None:
                end = len(lines)
            break

    if start is None:
        # append new section if missing
        with open("conc.yaml", "a") as f:
            f.write(f"\n{key}:\n  red: []\n  orange: []\n  blue: []\n  line_thickness: 2\n  num_zones: 1\n")
        start = len(lines)
        end = start

    block = lines[start:end]

    # --- patch specific color ---
    new_block = []
    inside_color = False
    point_idx = 0
    indent = "    "  # 4 spaces for list items

    for line in block:
        if line.strip().startswith(f"{zone_color}:"):
            inside_color = True
            new_block.append(line)
            continue

        if inside_color and line.strip().startswith("- ["):
            if point_idx < len(points):
                new_coords = f"[{points[point_idx][0]}, {points[point_idx][1]}]"
                updated_line = re.sub(r"\[.*?\]", new_coords, line)
                new_block.append(updated_line if updated_line.endswith("\n") else updated_line + "\n")
                point_idx += 1
            else:
                continue  # drop extras
        elif inside_color and (line.strip().startswith(("red:", "orange:", "blue:", "line_thickness:", "num_zones:"))):
            # stop patching when next key starts
            if point_idx < len(points):
                for pt in points[point_idx:]:
                    new_block.insert(-1, f"{indent}- [{pt[0]}, {pt[1]}]\n")
            inside_color = False
            new_block.append(line)
        else:
            new_block.append(line)

    # if section ends but still missing points
    if inside_color and point_idx < len(points):
        for pt in points[point_idx:]:
            new_block.append(f"{indent}- [{pt[0]}, {pt[1]}]\n")

    lines[start:end] = new_block

    with open("conc.yaml", "w") as f:
        f.writelines(lines)


# def save_points_to_conc(cam_index, points):
#     yaml = YAML()
#     yaml.preserve_quotes = True
#     yaml.width = 4096
#     yaml.indent(sequence=4, offset=2)
#     # ---------------- CONC.YAML (patch, no dump) ----------------
#         # ---------------- CONC.YAML (patch, no dump) ----------------
#     key = f"p{cam_index}_zone_coords"
#     with open("conc.yaml", "r") as f:
#         lines = f.readlines()

#     section = f"{key}:"
#     start, end = None, None
#     for i, line in enumerate(lines):
#         if line.strip().startswith(section):
#             start = i
#             for j in range(i + 1, len(lines)):
#                 if lines[j].strip() and not lines[j].startswith(" "):
#                     end = j
#                     break
#             if end is None:
#                 end = len(lines)
#             break

#     if start is None:
#         # append if missing
#         with open("conc.yaml", "a") as f:
#             f.write(f"\n{key}:\n  points:\n")
#             for pt in points:
#                 f.write(f"    - [{pt[0]}, {pt[1]}]\n")
#             f.write("\n  line_thickness: 2\n")
#         return

#     # --- Patch points block ---
#     block = lines[start:end]

#     # detect whether original had a blank line before line_thickness
#     had_blank_before_thickness = False
#     for i, line in enumerate(block):
#         if line.strip().startswith("line_thickness:") and i > 0:
#             if block[i-1].strip() == "":
#                 had_blank_before_thickness = True
#             break

#     new_block = []
#     inside_points = False
#     point_idx = 0

#     for line in block:
#         if line.strip().startswith("points:"):
#             inside_points = True
#             new_block.append(line)
#             continue

#         if inside_points and line.strip().startswith("- ["):
#             if point_idx < len(points):
#                 new_coords = f"[{points[point_idx][0]}, {points[point_idx][1]}]"
#                 updated_line = re.sub(r"\[.*?\]", new_coords, line)
#                 new_block.append(updated_line if updated_line.endswith("\n") else updated_line + "\n")
#                 point_idx += 1
#             else:
#                 continue  # drop extra old points
#         else:
#             new_block.append(line)

#     # Insert missing points strictly before line_thickness
#     # Insert missing points strictly before the *blank line + line_thickness*
#     if point_idx < len(points):
#         insert_at = None
#         for i, line in enumerate(new_block):
#             if line.strip().startswith("line_thickness:"):
#                 # 👇 check if there is a blank line before line_thickness
#                 if i > 0 and new_block[i-1].strip() == "":
#                     insert_at = i-1  # put new coords before the blank line
#                 else:
#                     insert_at = i
#                 break
#         if insert_at is None:
#             insert_at = len(new_block)

#         for pt in points[point_idx:]:
#             new_block.insert(insert_at, f"    - [{pt[0]}, {pt[1]}]\n")
#             insert_at += 1

#     # restore original blank line state
#     for i, line in enumerate(new_block):
#         if line.strip().startswith("line_thickness:") and i > 0:
#             if had_blank_before_thickness:
#                 if new_block[i-1].strip() != "":
#                     new_block.insert(i, "\n")
#             else:
#                 if new_block[i-1].strip() == "":
#                     del new_block[i-1]
#             break

#     lines[start:end] = new_block

#     with open("conc.yaml", "w") as f:
#         f.writelines(lines)

def sync_zones_from_conc_to_config(config_path="config.yaml", conc_path="conc.yaml"):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(sequence=4, offset=2)

    if not os.path.exists(conc_path) or not os.path.exists(config_path):
        return

    with open(config_path, "r") as f:
        cfg = yaml.load(f)

    with open(conc_path, "r") as f:
        conc_data = yaml.load(f)

    updated = False
    for key, val in (conc_data or {}).items():
        if key.startswith("p") and key.endswith("_zone_coords"):
            if "points" in val:  # conc.yaml style
                if key not in cfg:
                    # create a new structure if not present
                    cfg[key] = {
                        "red": val["points"],
                        "orange": [],
                        "blue": [],
                        "line_thickness": val.get("line_thickness", 2),
                        "num_zones": 1
                    }
                else:
                    # update existing config.yaml structure
                    cfg[key]["red"] = val["points"]
                    if "line_thickness" in val:
                        cfg[key]["line_thickness"] = val["line_thickness"]
                    cfg[key]["num_zones"] = 1
                updated = True
            else:
                # if conc.yaml already matches config.yaml style, just copy
                cfg[key] = val
                updated = True

    if updated:
        with open(config_path, "w") as f:
            yaml.dump(cfg, f)

# ---------------- EXTRA ----------------
def format_points(points):
    """Format coordinates as ruamel CommentedSeq for consistency."""
    outer = CommentedSeq()
    for p in points:
        inner = CommentedSeq(p)
        inner.fa.set_flow_style()
        outer.append(inner)
    return outer
