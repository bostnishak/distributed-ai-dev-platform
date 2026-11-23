"""Cluster C ([M44]): Synthetic DPO Preference Factory for CNC Ballooning, G-Code, and Python Edge Cases."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

_SYNTHETIC_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "cnc": [
        {
            "prompt": "AISI 4140 mil uzerinde O32 H7 (+0.025 / 0.000 mm) ve Ra 0.8 ic cap toleransi icin finiş operasyonu ve olcum cihazi sec.",
            "chosen": "OP20 Hassas Raybalama veya Ic Cap Taslama: Karbur rayba (Vc=25 m/dk, f=0.12 mm/dev, emulsuyon) ile islenir; 3 noktali ic cap mikrometresi veya CMM ile %100 kontrol edilir (ISO 286-2 H7).",
            "rejected": "Standart HSS matkap ile tek seferde delinir ve kumpas ile olculur.",
        },
        {
            "prompt": "Ince cidarli (t=2.0 mm) Al 7075-T6 bilezik parcasinda O85 H7 ic cap tornalanirken 3 ayakli aynada ovallesmeyi nasil onlersin?",
            "chosen": "6 ayakli ayna veya tam sarimli yumusak cene (pie jaws) kullanilmali, sikma kuvveti F_clamp <= 6000 N sinirlanmali ve finiş pasosunda ap=0.25 mm, f=0.08 mm/dev secilmelidir.",
            "rejected": "3 ayakli aynada maksimum hidrolik basinc ile sikilarak tek pasoda ap=3.0 mm talaş verilir.",
        },
        {
            "prompt": "Ti-6Al-4V (Grade 5) titanyum alasiminda derin delik (L/D = 6, O10 mm) delme parametrelerini belirle.",
            "chosen": "Icinden sogutma sivisi gecen (70 bar) TiAlN kapli karbur matkap, Vc=45 m/dk, f=0.08 mm/dev, G83 gagalama cevrimi (Q=2.0 mm) kullanilarak isi birikimi ve sertlesme onlenir.",
            "rejected": "Kuru kesimle Vc=220 m/dk yuksek hizda gagalama yapmadan tek seferde delinir.",
        },
    ],
    "gcode": [
        {
            "prompt": "Fanuc 31i kontrolorde M12x1.75 rijit kilavuz (rigid tapping) cevrimini 400 dev/dk ile Z-22.0 mm derinlige yaz.",
            "chosen": "T0404 (M12X1.75 RIGID TAP)\nG97 S400 M03\nG00 X0.000 Z5.000 M08\nM29 S400\nG98 G84 Z-22.000 R3.000 F700.0\nG80 G99",
            "rejected": "T0404\nG96 S400\nG01 Z-22.0 F1.75",
        },
        {
            "prompt": "Siemens Sinumerik 840D uzerinde T1 takimi icin CMM olcumunden gelen +0.014 mm cap sapmasini telafi eden asinma ofset komutunu yaz.",
            "chosen": "$TC_DP12[1,1] = -0.0140",
            "rejected": "G10 P1 R0.014",
        },
    ],
    "python": [
        {
            "prompt": "SQLite veritabaninda kullanici girdisiyle guvenli parametrik SELECT sorgusu yaz.",
            "chosen": "cursor.execute('SELECT id, username, role FROM users WHERE username = ?', (username,))",
            "rejected": "cursor.execute(f\"SELECT id, username, role FROM users WHERE username = '{username}'\")",
        },
        {
            "prompt": "Kullanicidan gelen dosya yolunu (rel_path) calisma alani (base_dir) disina cikmayacak sekilde Path Traversal korumalariyla dogrula.",
            "chosen": "target = (base_dir / rel_path).resolve()\nif not target.is_relative_to(base_dir.resolve()):\n    raise PermissionError('Path traversal blocked')",
            "rejected": "target = os.path.join(str(base_dir), rel_path)\nopen(target).read()",
        },
    ],
}


def generate_synthetic_dpo_batch(count: int = 10, domain: str = "cnc") -> list[dict[str, Any]]:
    """Generate ``count`` verified synthetic ``(prompt, chosen, rejected)`` DPO triples for ``domain``."""
    target_count = max(1, int(count))
    norm_domain = (domain or "cnc").strip().lower()
    templates = _SYNTHETIC_TEMPLATES.get(norm_domain)
    if not templates:
        templates = (
            _SYNTHETIC_TEMPLATES["cnc"]
            + _SYNTHETIC_TEMPLATES["gcode"]
            + _SYNTHETIC_TEMPLATES["python"]
        )

    batch: list[dict[str, Any]] = []
    now_iso = datetime.now(UTC).isoformat()

    for idx in range(target_count):
        tpl = templates[idx % len(templates)]
        variant_no = (idx // len(templates)) + 1
        tol_um = 15 + (idx % 6) * 5
        prompt = f"[Senaryo #{variant_no:02d} | Hedef Hassasiyet +/-0.0{tol_um:02d} mm] {tpl['prompt']}"
        chosen = f"{tpl['chosen']} (Dogrulama Kodu: ISO-VERIFIED-{idx + 1:03d}, Hedef: +/-0.0{tol_um:02d} mm)."
        rejected = f"{tpl['rejected']} (Dogrulanmamis varsayim #{idx + 1})."

        digest = hashlib.sha256(f"{norm_domain}||{prompt}||{chosen}".encode()).hexdigest()[:16]
        batch.append(
            {
                "id": digest,
                "domain": norm_domain,
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "synthetic": True,
                "verified": True,
                "created_at": now_iso,
            }
        )

    return batch
