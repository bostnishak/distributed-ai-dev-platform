"""Cluster D ([M47]): 3D Solid Model 3-View + Section 2D-3D MBD Projection Generator."""

from __future__ import annotations

from typing import Any

from cad_cam_physics import analyze_3d_cad_file


def project_3d_to_2d_views(
    cad_result_or_bytes: dict[str, Any] | bytes,
    filename: str = "part.step",
) -> dict[str, Any]:
    """Generate 3 orthogonal 2D views (FRONT, TOP, RIGHT) plus SECTION_A-A from a 3D CAD model
    and map 2D inspection balloons to 3D topological ``Face_ID`` identifiers.
    """
    if isinstance(cad_result_or_bytes, (bytes, bytearray)):
        cad_data = analyze_3d_cad_file(filename, bytes(cad_result_or_bytes))
    elif isinstance(cad_result_or_bytes, dict):
        cad_data = cad_result_or_bytes
    else:
        raise TypeError("cad_result_or_bytes must be a dict or bytes")

    bbox = cad_data.get("bounding_box_mm") or {"x": 50.0, "y": 50.0, "z": 25.0}
    dx = float(bbox.get("x", 50.0))
    dy = float(bbox.get("y", 50.0))
    dz = float(bbox.get("z", 25.0))

    features = list(cad_data.get("features") or [])
    mbd_matches = list(cad_data.get("mbd_2d_3d_matches") or [])

    if not mbd_matches and features:
        views_order = ["FRONT", "TOP", "SECTION_A-A", "RIGHT"]
        for idx, feat in enumerate(features):
            nominal = (
                feat.get("diameter_mm")
                or feat.get("width_mm")
                or feat.get("radius_mm")
                or feat.get("thickness_mm")
                or 10.0
            )
            mbd_matches.append(
                {
                    "balloon_no": idx + 1,
                    "feature_id": str(feat.get("feature_id") or f"FEAT-{idx + 1:02d}"),
                    "feature_type": str(feat.get("type") or "FEATURE"),
                    "face_id": str(feat.get("face_id") or f"#F{100 + idx}"),
                    "view": views_order[idx % len(views_order)],
                    "nominal_mm": float(nominal),
                    "tolerance": str(feat.get("tolerance_class") or "ISO 2768-mK"),
                }
            )

    views: dict[str, dict[str, Any]] = {
        "FRONT": {
            "plane": "XZ",
            "width_mm": dx,
            "height_mm": dz,
            "balloons": [m for m in mbd_matches if m.get("view") == "FRONT"],
        },
        "TOP": {
            "plane": "XY",
            "width_mm": dx,
            "height_mm": dy,
            "balloons": [m for m in mbd_matches if m.get("view") == "TOP"],
        },
        "RIGHT": {
            "plane": "YZ",
            "width_mm": dy,
            "height_mm": dz,
            "balloons": [m for m in mbd_matches if m.get("view") == "RIGHT"],
        },
        "SECTION_A-A": {
            "plane": "XZ_MIDPLANE",
            "cutting_plane_y_mm": 0.0,
            "width_mm": dx,
            "height_mm": dz,
            "balloons": [m for m in mbd_matches if m.get("view") in ("SECTION_A-A", "DETAIL_B")],
        },
    }

    face_to_balloon = {str(m["face_id"]): int(m["balloon_no"]) for m in mbd_matches}

    return {
        "product_name": str(cad_data.get("product_name") or filename),
        "bounding_box_mm": {"x": dx, "y": dy, "z": dz},
        "views": views,
        "view_names": list(views.keys()),
        "mbd_2d_3d_matches": mbd_matches,
        "face_to_balloon_map": face_to_balloon,
        "total_balloons": len(mbd_matches),
    }


__all__ = [
    "analyze_3d_cad_file",
    "project_3d_to_2d_views",
]
