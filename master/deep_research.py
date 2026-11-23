"""Cluster A (`[M10]` & `[M11]`): Deep Research Engine & Rich AI PowerPoint (.pptx) Presentation Builder.

- `decompose_research_questions`: breaks a complex topic into structured analytical dimensions.
- `build_pptx_presentation`: creates a themed, multi-slide OpenXML `.pptx` presentation with full-bleed
  backgrounds, accent shapes, two-column callout cards, Turkish-safe Segoe UI typography, and real
  PowerPoint slide transitions (`fade`, `push`, `wipe`, `cover`) using pure Python `zipfile`.
- `generate_ai_pptx_presentation`: uses the local Ollama LLM to research the user's exact topic,
  pick a topic-appropriate visual theme and transitions, and compile a complete `.pptx` file.
"""

from __future__ import annotations

import html
import json
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

import config
import multimodal_studio as mms

TOPIC_THEMES: dict[str, dict[str, str]] = {
    "history": {
        "name": "Tarih ve Medeniyet (Antik Altın & Gece Laciverti)",
        "bg": "141824",
        "card": "1E2436",
        "accent": "D97706",
        "accent2": "F59E0B",
        "text": "F8FAFC",
        "muted": "CBD5E1",
        "transition": "fade",
    },
    "tech": {
        "name": "Teknoloji ve Bilim (Koyu Uzay & Siyan)",
        "bg": "0B1120",
        "card": "162033",
        "accent": "06B6D4",
        "accent2": "6366F1",
        "text": "F8FAFC",
        "muted": "CBD5E1",
        "transition": "push",
    },
    "nature": {
        "name": "Doğa ve Sağlık (Orman Yeşili & Zümrüt)",
        "bg": "0D1F1A",
        "card": "163029",
        "accent": "10B981",
        "accent2": "34D399",
        "text": "F0FDF4",
        "muted": "BBF7D0",
        "transition": "wipe",
    },
    "light": {
        "name": "Aydınlık Kurumsal (Krem & Çivit)",
        "bg": "F8FAFC",
        "card": "FFFFFF",
        "accent": "4F46E5",
        "accent2": "0EA5E9",
        "text": "0F172A",
        "muted": "475569",
        "transition": "fade",
    },
    "corporate": {
        "name": "Modern Kurumsal (Koyu Arduvaz & İndigo)",
        "bg": "0F172A",
        "card": "1E293B",
        "accent": "4F46E5",
        "accent2": "38BDF8",
        "text": "F8FAFC",
        "muted": "CBD5E1",
        "transition": "cover",
    },
}


def _pick_theme_for_topic(prompt: str) -> dict[str, str]:
    low = (prompt or "").lower()
    if any(k in low for k in ("açık tema", "acik tema", "beyaz arka plan", "aydınlık")):
        return dict(TOPIC_THEMES["light"])
    if any(k in low for k in ("tarih", "medeniyet", "uygarlık", "antik", "osmanlı", "insanlık", "savaş", "arkeoloji", "sanat")):
        return dict(TOPIC_THEMES["history"])
    if any(k in low for k in ("doğa", "çevre", "iklim", "biyoloji", "sağlık", "tıp", "tarım", "enerji", "yeşil")):
        return dict(TOPIC_THEMES["nature"])
    if any(k in low for k in ("yapay zeka", "yazılım", "bilgisayar", "uzay", "fizik", "robot", "teknoloji", "siber", "veri")):
        return dict(TOPIC_THEMES["tech"])
    return dict(TOPIC_THEMES["corporate"])


def _safe_hex(val: Any, fallback: str) -> str:
    s = re.sub(r"[^0-9A-Fa-f]", "", str(val or ""))
    return s.upper() if len(s) == 6 else fallback


def _transition_xml(kind: str) -> str:
    k = (kind or "fade").strip().lower()
    if k == "push":
        return '<p:transition spd="med"><p:push dir="l"/></p:transition>'
    if k == "wipe":
        return '<p:transition spd="med"><p:wipe dir="r"/></p:transition>'
    if k == "cover":
        return '<p:transition spd="med"><p:cover dir="l"/></p:transition>'
    if k == "split":
        return '<p:transition spd="med"><p:split orient="horz" dir="out"/></p:transition>'
    return '<p:transition spd="med"><p:fade/></p:transition>'


def decompose_research_questions(topic: str) -> list[str]:
    """Decompose a broad research query into 4 orthogonal analytical dimensions."""
    clean = topic.strip().rstrip("?.!")
    return [
        f"1. {clean} - Temel Kavramlar, Tarihsel Gelişim ve Arka Plan",
        f"2. {clean} - Temel Dönüm Noktaları, Bulgular ve Karşılaştırmalı Analiz",
        f"3. {clean} - Güncel Etkiler, Fırsatlar ve Kritik Sorunlar",
        f"4. {clean} - Gelecek Perspektifi ve Özet Çıkarımlar",
    ]


def build_pptx_presentation(
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    out_path: Path | None = None,
    theme: dict[str, str] | None = None,
) -> Path:
    """Build a themed, animated, multi-slide PowerPoint (.pptx) file using pure OpenXML ZIP packaging."""
    if out_path is None:
        fid = f"pres-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.pptx"
        out_path = mms.media_dir() / fid
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pal = theme or _pick_theme_for_topic(title)
    bg_hex = _safe_hex(pal.get("bg"), "0F172A")
    card_hex = _safe_hex(pal.get("card"), "1E293B")
    acc_hex = _safe_hex(pal.get("accent"), "4F46E5")
    acc2_hex = _safe_hex(pal.get("accent2"), "38BDF8")
    txt_hex = _safe_hex(pal.get("text"), "F8FAFC")
    muted_hex = _safe_hex(pal.get("muted"), "CBD5E1")
    trans_kind = str(pal.get("transition") or "fade")

    all_slides = [{"_cover": True, "title": title, "subtitle": subtitle or "Yapay Zeka Araştırma Sunumu"}, *(slides or [])]
    n_slides = len(all_slides)

    content_types_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, n_slides + 1)
    )
    content_types_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
{content_types_overrides}
</Types>"""

    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""

    pres_rels_items = "\n".join(
        f'  <Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, n_slides + 1)
    )
    pres_rels_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{pres_rels_items}
</Relationships>"""

    sld_id_items = "\n".join(
        f'    <p:sldId id="{255 + i}" r:id="rId{i}"/>'
        for i in range(1, n_slides + 1)
    )
    presentation_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>
{sld_id_items}
  </p:sldIdLst>
  <p:sldSz cx="9144000" cy="5143500" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""

    trans_xml = _transition_xml(trans_kind)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels_xml)

        for idx, sdata in enumerate(all_slides, start=1):
            stitle = html.escape(str(sdata.get("title") or f"Slayt {idx}"))
            if sdata.get("_cover"):
                ssub = html.escape(str(sdata.get("subtitle") or ""))
                slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg_hex}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="LeftAccent"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="0" y="0"/><a:ext cx="280000" cy="5143500"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{acc_hex}"/></a:solidFill>
        </p:spPr>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="CoverCard"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="720000" y="920000"/><a:ext cx="7700000" cy="3300000"/></a:xfrm>
          <a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{card_hex}"/></a:solidFill>
          <a:ln w="19050"><a:solidFill><a:srgbClr val="{acc_hex}"/></a:solidFill></a:ln>
        </p:spPr>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="4" name="AccentBar"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="1100000" y="1380000"/><a:ext cx="1400000" cy="75000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{acc2_hex}"/></a:solidFill>
        </p:spPr>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="5" name="CoverTitle"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="1100000" y="1600000"/><a:ext cx="6900000" cy="1200000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square"/>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="tr-TR" sz="3800" b="1" dirty="0"><a:solidFill><a:srgbClr val="{txt_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{stitle}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="6" name="CoverSub"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="1100000" y="2900000"/><a:ext cx="6900000" cy="950000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square"/>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="tr-TR" sz="2000" dirty="0"><a:solidFill><a:srgbClr val="{muted_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{ssub}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  {trans_xml}
</p:sld>"""
                zf.writestr(f"ppt/slides/slide{idx}.xml", slide_xml)
                continue

            kicker = html.escape(str(sdata.get("kicker") or f"BÖLÜM {idx - 1}"))
            key_fact = html.escape(str(sdata.get("key_fact") or ""))
            bullets = [html.escape(str(b).strip()) for b in (sdata.get("bullets") or []) if str(b).strip()]
            if not bullets:
                bullets = [html.escape(str(sdata.get("content") or ""))]

            paragraphs_xml = "\n".join(
                f"""          <a:p>
            <a:pPr spcAft="120000"/>
            <a:r><a:rPr lang="tr-TR" sz="1750" dirty="0"><a:solidFill><a:srgbClr val="{txt_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>• {b}</a:t></a:r>
          </a:p>"""
                for b in bullets[:6]
            )

            has_callout = bool(key_fact)
            left_w = 5200000 if has_callout else 8229600
            callout_xml = ""
            if has_callout:
                callout_xml = f"""      <p:sp>
        <p:nvSpPr><p:cNvPr id="7" name="CalloutCard"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="5880000" y="1380000"/><a:ext cx="2800000" cy="3180000"/></a:xfrm>
          <a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{card_hex}"/></a:solidFill>
          <a:ln w="19050"><a:solidFill><a:srgbClr val="{acc2_hex}"/></a:solidFill></a:ln>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square" lIns="180000" rIns="180000" tIns="220000" bIns="180000"/>
          <a:lstStyle/>
          <a:p><a:pPr spcAft="140000"/><a:r><a:rPr lang="tr-TR" sz="1300" b="1" dirty="0"><a:solidFill><a:srgbClr val="{acc2_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>ÖNEMLİ NOT / DÖNÜM NOKTASI</a:t></a:r></a:p>
          <a:p><a:r><a:rPr lang="tr-TR" sz="1650" dirty="0"><a:solidFill><a:srgbClr val="{txt_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{key_fact}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>"""

            slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg_hex}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="TopBar"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="0" y="0"/><a:ext cx="9144000" cy="110000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{acc_hex}"/></a:solidFill>
        </p:spPr>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Kicker"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="457200" y="250000"/><a:ext cx="6000000" cy="300000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="tr-TR" sz="1200" b="1" dirty="0"><a:solidFill><a:srgbClr val="{acc2_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{kicker}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="4" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="457200" y="540000"/><a:ext cx="8229600" cy="680000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square"/>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="tr-TR" sz="2800" b="1" dirty="0"><a:solidFill><a:srgbClr val="{txt_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{stitle}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="5" name="ContentCard"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="457200" y="1380000"/><a:ext cx="{left_w}" cy="3180000"/></a:xfrm>
          <a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{card_hex}"/></a:solidFill>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square" lIns="200000" rIns="180000" tIns="200000" bIns="160000"/>
          <a:lstStyle/>
{paragraphs_xml}
        </p:txBody>
      </p:sp>
{callout_xml}
      <p:sp>
        <p:nvSpPr><p:cNvPr id="8" name="Footer"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="457200" y="4720000"/><a:ext cx="8229600" cy="300000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="tr-TR" sz="1100" dirty="0"><a:solidFill><a:srgbClr val="{muted_hex}"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{html.escape(title)}  ·  Slayt {idx} / {n_slides}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  {trans_xml}
</p:sld>"""
            zf.writestr(f"ppt/slides/slide{idx}.xml", slide_xml)

    return out_path


async def generate_ai_pptx_presentation(prompt: str) -> dict[str, Any]:
    """Research the user's exact topic via local Ollama LLM and build a themed, animated .pptx deck."""
    model = await mms.pick_best_model("deep")
    theme = _pick_theme_for_topic(prompt)

    m_cnt = re.search(r"\b(\d{1,2})\s*(?:slayt|sayfa|slide)", prompt, re.IGNORECASE)
    slide_count = max(4, min(14, int(m_cnt.group(1)) - 1)) if m_cnt else 6

    sys_prompt = (
        "Sen kıdemli bir araştırmacı ve profesyonel sunum tasarımcısısın.\n"
        f"Kullanıcının istediği konuyu derinlemesine araştırıp TAM OLARAK {slide_count} içerik slaytından oluşan "
        "zengin, öğretici ve konuya %100 sadık bir PowerPoint sunum planını SADECE geçerli JSON olarak döndür:\n"
        "{\n"
        '  "title": "Sunumun Ana Başlığı",\n'
        '  "subtitle": "Konuyu özetleyen çarpıcı alt başlık",\n'
        '  "transition": "fade",\n'
        '  "slides": [\n'
        "    {\n"
        '      "kicker": "DÖNEM / BÖLÜM ETİKETİ",\n'
        '      "title": "Slayt Başlığı",\n'
        '      "bullets": [\n'
        '        "Bilgilendirici, somut ve akıcı 1. madde",\n'
        '        "Tarih/veri/kavram içeren 2. madde",\n'
        '        "Önemli etki veya örnek içeren 3. madde",\n'
        '        "Özetleyici 4. madde"\n'
        "      ],\n"
        '      "key_fact": "Sağdaki vurgu kartında gösterilecek en önemli tarih, sayı veya özet bilgi."\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "KESİN KURALLAR:\n"
        "- Kullanıcının istediği konuya ve dile %100 sadık kal; asla konu dışı genel şablon metinleri yazma.\n"
        "- transition değeri şunlardan biri olsun: fade, push, wipe, cover.\n"
        "- Türkçe karakterleri (Ç, Ğ, İ, Ö, Ş, Ü, ç, ğ, ı, ö, ş, ü) kusursuz kullan. Asla emoji kullanma."
    )

    spec: dict[str, Any] = {
        "title": prompt.strip()[:72],
        "subtitle": "Araştırma ve Görsel Sunum",
        "transition": theme["transition"],
        "slides": [],
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.35, "num_predict": 3600},
                },
            )
            if resp.status_code == 200:
                raw = resp.json().get("message", {}).get("content", "")
                m = re.search(r"\{[\s\S]*\}", raw)
                if m:
                    cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(0))
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict) and parsed.get("slides"):
                        spec.update(parsed)
    except Exception:
        pass

    if not spec.get("slides"):
        spec["slides"] = [
            {
                "kicker": f"BÖLÜM {i + 1}",
                "title": q.split(" - ")[-1] if " - " in q else q,
                "bullets": [q],
                "key_fact": f"{spec['title']} temel değerlendirmesi.",
            }
            for i, q in enumerate(decompose_research_questions(prompt))
        ]

    if spec.get("transition") in ("fade", "push", "wipe", "cover", "split"):
        theme["transition"] = str(spec["transition"])

    out_path = build_pptx_presentation(
        title=str(spec.get("title") or prompt[:70]),
        subtitle=str(spec.get("subtitle") or "Yapay Zeka Sunumu"),
        slides=spec["slides"],
        theme=theme,
    )
    return {
        "title": str(spec.get("title") or prompt[:70]),
        "subtitle": str(spec.get("subtitle") or ""),
        "theme_name": theme["name"],
        "transition": theme["transition"],
        "slides": spec["slides"],
        "slide_count": len(spec["slides"]) + 1,
        "model": model,
        "filename": out_path.name,
        "url": f"/api/assistant/media/{out_path.name}",
    }
