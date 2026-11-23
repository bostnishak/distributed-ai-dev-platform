"""Cluster A (`[M10]` & `[M11]`): Deep Research Engine & Rich AI PowerPoint (.pptx) Presentation Builder.

- `decompose_research_questions`: breaks a complex topic into structured analytical dimensions.
- `build_pptx_presentation`: creates a themed, multi-slide OpenXML `.pptx` presentation with full-bleed
  backgrounds, accent shapes, two-column callout cards, Turkish-safe Segoe UI typography, and real
  PowerPoint slide transitions (`fade`, `push`, `wipe`, `cover`) using pure Python `zipfile`.
- `generate_ai_pptx_presentation`: uses the local Ollama LLM to research the user's exact topic,
  pick a topic-appropriate visual theme and transitions, and compile a complete `.pptx` file.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches, Pt

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
    ns = nsdecls("p")
    if k == "push":
        return f'<p:transition {ns} spd="med"><p:push dir="l"/></p:transition>'
    if k == "wipe":
        return f'<p:transition {ns} spd="med"><p:wipe dir="r"/></p:transition>'
    if k == "cover":
        return f'<p:transition {ns} spd="med"><p:cover dir="l"/></p:transition>'
    if k == "split":
        return f'<p:transition {ns} spd="med"><p:split orient="horz" dir="out"/></p:transition>'
    return f'<p:transition {ns} spd="med"><p:fade/></p:transition>'


def _rgb(hex_str: str) -> RGBColor:
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def _apply_slide_transition(slide: Any, kind: str) -> None:
    """Attach a schema-valid PowerPoint slide transition element (<p:transition>) to the slide."""
    trans_el = parse_xml(_transition_xml(kind))
    slide._element.append(trans_el)


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
    """Build a 100% Microsoft PowerPoint-compliant 16:9 themed & animated .pptx deck using python-pptx."""
    if out_path is None:
        fid = f"pres-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.pptx"
        out_path = mms.media_dir() / fid
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pal = theme or _pick_theme_for_topic(title)
    bg_rgb = _rgb(_safe_hex(pal.get("bg"), "0F172A"))
    card_rgb = _rgb(_safe_hex(pal.get("card"), "1E293B"))
    acc_rgb = _rgb(_safe_hex(pal.get("accent"), "4F46E5"))
    acc2_rgb = _rgb(_safe_hex(pal.get("accent2"), "38BDF8"))
    txt_rgb = _rgb(_safe_hex(pal.get("text"), "F8FAFC"))
    muted_rgb = _rgb(_safe_hex(pal.get("muted"), "CBD5E1"))
    trans_kind = str(pal.get("transition") or "fade")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    all_slides = [{"_cover": True, "title": title, "subtitle": subtitle or "Yapay Zeka Araştırma Sunumu"}, *(slides or [])]
    n_slides = len(all_slides)

    for idx, sdata in enumerate(all_slides, start=1):
        slide = prs.slides.add_slide(blank_layout)
        # Full-bleed themed background
        bg_fill = slide.background.fill
        bg_fill.solid()
        bg_fill.fore_color.rgb = bg_rgb
        _apply_slide_transition(slide, trans_kind)

        stitle = str(sdata.get("title") or f"Slayt {idx}")

        if sdata.get("_cover"):
            ssub = str(sdata.get("subtitle") or "")
            # Left vertical accent stripe
            stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.38), Inches(7.5))
            stripe.fill.solid()
            stripe.fill.fore_color.rgb = acc_rgb
            stripe.line.fill.background()

            # Rounded cover card
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.05), Inches(1.35), Inches(11.2), Inches(4.8))
            card.fill.solid()
            card.fill.fore_color.rgb = card_rgb
            card.line.color.rgb = acc_rgb
            card.line.width = Pt(1.75)

            # Accent bar inside cover card
            bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.6), Inches(2.0), Inches(2.0), Inches(0.1))
            bar.fill.solid()
            bar.fill.fore_color.rgb = acc2_rgb
            bar.line.fill.background()

            # Cover title
            tb_title = slide.shapes.add_textbox(Inches(1.6), Inches(2.3), Inches(10.1), Inches(1.8))
            tf = tb_title.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = stitle
            r.font.name = "Segoe UI"
            r.font.size = Pt(38)
            r.font.bold = True
            r.font.color.rgb = txt_rgb

            # Cover subtitle
            tb_sub = slide.shapes.add_textbox(Inches(1.6), Inches(4.25), Inches(10.1), Inches(1.35))
            tf2 = tb_sub.text_frame
            tf2.word_wrap = True
            p2 = tf2.paragraphs[0]
            r2 = p2.add_run()
            r2.text = ssub
            r2.font.name = "Segoe UI"
            r2.font.size = Pt(20)
            r2.font.color.rgb = muted_rgb
            continue

        kicker = str(sdata.get("kicker") or f"BÖLÜM {idx - 1}")
        key_fact = str(sdata.get("key_fact") or "").strip()
        notes_txt = str(sdata.get("notes") or "").strip()
        bullets = [str(b).strip() for b in (sdata.get("bullets") or []) if str(b).strip()]
        if not bullets:
            bullets = [str(sdata.get("content") or "")]

        # Top accent bar
        top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.16))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = acc_rgb
        top_bar.line.fill.background()

        # Kicker label
        tb_kick = slide.shapes.add_textbox(Inches(0.65), Inches(0.36), Inches(8.0), Inches(0.4))
        p_k = tb_kick.text_frame.paragraphs[0]
        r_k = p_k.add_run()
        r_k.text = kicker.upper()
        r_k.font.name = "Segoe UI"
        r_k.font.size = Pt(12)
        r_k.font.bold = True
        r_k.font.color.rgb = acc2_rgb

        # Slide title
        tb_t = slide.shapes.add_textbox(Inches(0.65), Inches(0.76), Inches(12.0), Inches(0.95))
        tf_t = tb_t.text_frame
        tf_t.word_wrap = True
        p_t = tf_t.paragraphs[0]
        r_t = p_t.add_run()
        r_t.text = stitle
        r_t.font.name = "Segoe UI"
        r_t.font.size = Pt(28)
        r_t.font.bold = True
        r_t.font.color.rgb = txt_rgb

        # Main content card
        has_callout = bool(key_fact)
        card_w = Inches(7.7) if has_callout else Inches(12.0)
        c_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.65), Inches(1.9), card_w, Inches(4.75))
        c_card.fill.solid()
        c_card.fill.fore_color.rgb = card_rgb
        c_card.line.fill.background()
        tf_c = c_card.text_frame
        tf_c.word_wrap = True
        tf_c.margin_left = Inches(0.32)
        tf_c.margin_right = Inches(0.28)
        tf_c.margin_top = Inches(0.28)
        tf_c.margin_bottom = Inches(0.24)
        for bi, btxt in enumerate(bullets[:6]):
            pb = tf_c.paragraphs[0] if bi == 0 else tf_c.add_paragraph()
            pb.space_after = Pt(11)
            rb = pb.add_run()
            rb.text = f"•  {btxt}"
            rb.font.name = "Segoe UI"
            rb.font.size = Pt(16.5)
            rb.font.color.rgb = txt_rgb

        # Right-hand Key Fact callout card
        if has_callout:
            k_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.65), Inches(1.9), Inches(4.0), Inches(4.75))
            k_card.fill.solid()
            k_card.fill.fore_color.rgb = card_rgb
            k_card.line.color.rgb = acc2_rgb
            k_card.line.width = Pt(1.75)
            tf_k = k_card.text_frame
            tf_k.word_wrap = True
            tf_k.margin_left = Inches(0.28)
            tf_k.margin_right = Inches(0.28)
            tf_k.margin_top = Inches(0.35)

            pk_head = tf_k.paragraphs[0]
            pk_head.space_after = Pt(14)
            rk_head = pk_head.add_run()
            rk_head.text = "ÖNEMLİ NOT / DÖNÜM NOKTASI"
            rk_head.font.name = "Segoe UI"
            rk_head.font.size = Pt(12.5)
            rk_head.font.bold = True
            rk_head.font.color.rgb = acc2_rgb

            pk_body = tf_k.add_paragraph()
            rk_body = pk_body.add_run()
            rk_body.text = key_fact
            rk_body.font.name = "Segoe UI"
            rk_body.font.size = Pt(16)
            rk_body.font.color.rgb = txt_rgb

        # Footer
        tb_f = slide.shapes.add_textbox(Inches(0.65), Inches(6.92), Inches(12.0), Inches(0.35))
        pf = tb_f.text_frame.paragraphs[0]
        rf = pf.add_run()
        rf.text = f"{title}   |   Slayt {idx} / {n_slides}"
        rf.font.name = "Segoe UI"
        rf.font.size = Pt(10.5)
        rf.font.color.rgb = muted_rgb

        if notes_txt:
            slide.notes_slide.notes_text_frame.text = notes_txt

    prs.save(str(out_path))
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
        import gateway

        res = await gateway.default_client.chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ],
            model=model,
            profile="analytic",
            num_predict=3600,
            timeout_s=120.0,
            feature="deep_research",
            max_retries=0,
        )
        raw = res.content
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and parsed.get("slides"):
                spec.update(parsed)
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
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
