"""Bring docs/plan-v3/PROGRESS.json in line with what was actually verified.

Usage: python scripts/audit/reconcile_progress.py <commit-with-the-new-tests>

1. Normalises string evidence ("path::test") into the {tests, commit, eval_report} form the plan tool requires.
2. Downgrades 'done' claims whose implementation was inspected and found to be a flag, a literal string or a record
   that nothing consumes, and records why in `note`.
3. Re-points items whose behaviour is now really tested at the new evidence.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRESS = ROOT / "docs" / "plan-v3" / "PROGRESS.json"
NEW_COMMIT = sys.argv[1]


def introduced_in(path: str) -> str:
    out = subprocess.run(  # noqa: S603
        ["git", "log", "--diff-filter=A", "-1", "--format=%h", "--", path],  # noqa: S607
        capture_output=True, text=True, cwd=ROOT, check=False,
    ).stdout.strip()
    return out or NEW_COMMIT


DOWNGRADE = {
    "SOH-06": ("claimed_without_evidence", "ENHANCEMENT_HOOKS.voiceMode yalnizca true bayragi; sesli sohbet akisi yok."),
    "SOH-07": ("claimed_without_evidence", "ENHANCEMENT_HOOKS.modelPicker yalnizca true bayragi; model secici arayuzu yok."),
    "OPR-04": ("claimed_without_evidence", "Yuk dengeleyici/lider secimi yok; onceki cevap sabit bir metindi, simdi 'false' diye dogru raporlaniyor."),
    "DOS-04": ("open", "Bulut surucu baglayicisi yok: /connectors/status 'configured: false' donuyor."),
    "DOS-05": ("open", "GitHub baglayicisi yok: /connectors/status 'configured: false' donuyor."),
    "MED-01": ("open", "Ses donusturme yok: audio_convert_available false."),
    "MED-04": ("open", "Video uretimi yok: video_generate_available false."),
    "ARS-01": ("claimed_without_evidence", "Kaynak PDF indirme/dizinleme kodu yok; yalniz 'download_source_policy' metni var."),
    "ARS-04": ("claimed_without_evidence", "Sayfa arsivleyen kod yok; _ARCHIVED_PAGES hicbir yerde doldurulmuyor."),
    "KOD-08": ("partial", "Yalniz dort regex ile python->js; dogrulama ve baska dil cifti yok."),
    "SUN-02": ("partial", "Ikon kitapligi dort SVG'den ibaret."),
    "AJN-01": ("partial", "Ozel ajanlar kaydediliyor ama sohbet/gorev akisi onlari kullanmiyor."),
    "AJN-06": ("partial", "Onay kapilari kaydediliyor; hicbir adim onay beklemiyor."),
    "OPR-02": ("partial", "remediate_actions yalniz adlar; calistiran kod yok."),
}

NEW_EVIDENCE = {
    "GUV-01": (["master/tests/test_cronjobs_and_kvstore.py"], "TOTP artik giriste zorunlu: kayit, onay, kapatma ve yanlis kod reddi test edildi."),
    "AJN-02": (["master/tests/test_cronjobs_and_kvstore.py"], "Cron ifadesi dogrulanir, gorevler dakikada bir gercekten calisir, sonuc kaydedilir, yeniden baslatmada kalir."),
    "AJN-05": (["master/tests/test_cronjobs_and_kvstore.py"], "Bakim modundaki ajan bekleyen is olsa da yeni gorev almaz."),
    "ARS-05": (["master/tests/test_cronjobs_and_kvstore.py"], "Sorgu master modeliyle gercekten cevriliyor (onceden sabit ek metin)."),
    "HAF-01": (["master/tests/test_cronjobs_and_kvstore.py"], "Proje talimatlari artik veritabaninda; yeniden baslatmada kaybolmaz."),
    "SOH-03": (["master/tests/test_cronjobs_and_kvstore.py"], "Arsivlenen sohbetler veritabaninda kalir."),
    "DOS-07": (["master/tests/test_cronjobs_and_kvstore.py"], "Belge surumleri veritabaninda kalir."),
}
XSS_EVIDENCE = ["master/tests/test_xss_sanitizer_browser.py", "frontend/tests/sanitizer.test.mjs"]

data = json.loads(PROGRESS.read_text(encoding="utf-8"))
items = data["items"]
changed = {"normalised": 0, "downgraded": 0, "re-evidenced": 0}

for key, entry in items.items():
    ev = entry.get("evidence")
    if isinstance(ev, str):
        paths = re.findall(r"[\w/.\-]+\.(?:py|mjs)", ev)
        entry["evidence"] = {"tests": [ev], "commit": introduced_in(paths[0]) if paths else NEW_COMMIT, "eval_report": ""}
        changed["normalised"] += 1

for key, (status, why) in DOWNGRADE.items():
    items[key]["status"] = status
    items[key]["note"] = why
    changed["downgraded"] += 1

for key, (tests, why) in NEW_EVIDENCE.items():
    items[key] = {"status": "done", "evidence": {"tests": tests, "commit": NEW_COMMIT, "eval_report": ""}, "note": why}
    changed["re-evidenced"] += 1

for n in range(1, 40):
    key = f"XSS-{n:02d}"
    if key in items:
        items[key] = {
            "status": "done",
            "evidence": {"tests": XSS_EVIDENCE, "commit": NEW_COMMIT, "eval_report": ""},
            "note": "Duzenli ifade kara listesi saldirilari geciriyordu (7/25); DOM tabanli izin listesiyle yeniden yazildi, gercek tarayicida 25/25 etkisiz.",
        }
        changed["re-evidenced"] += 1

PROGRESS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(changed)
