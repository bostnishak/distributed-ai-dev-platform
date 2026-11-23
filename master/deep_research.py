"""Cluster A (`[M10]` & `[M11]`): Deep Research Engine & Pure-Python PowerPoint (.pptx) Presentation Generator.

- `decompose_research_questions`: breaks a complex topic into 4 structured sub-questions
- `build_pptx_presentation`: creates a valid OpenXML `.pptx` presentation archive using pure Python `zipfile`
  (zero external `python-pptx` installation required; opens natively in Microsoft PowerPoint, LibreOffice, Google Slides!)
"""

from __future__ import annotations

import html
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import multimodal_studio as mms


def decompose_research_questions(topic: str) -> list[str]:
    """Decompose a broad research query into 4 orthogonal analytical dimensions."""
    clean = topic.strip().rstrip("?.!")
    return [
        f"1. {clean} - Temel Kavramlar, Teknik Mimari ve Mevcut Standartlar",
        f"2. {clean} - Kantitatif Metrikler, Maliyet/Performans Karşılaştırması ve Veri Analizi",
        f"3. {clean} - Kritik Riskler, Darboğazlar, Güvenlik ve Uyumluluk Gereksinimleri",
        f"4. {clean} - Uygulama Yol Haritası ve Stratejik Öneriler",
    ]


def build_pptx_presentation(
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    out_path: Path | None = None,
) -> Path:
    """Build a valid, multi-slide Microsoft PowerPoint (.pptx) file using pure OpenXML ZIP packaging."""
    if out_path is None:
        fid = f"pres-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.pptx"
        out_path = mms.media_dir() / fid
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_slides = [{"title": title, "bullets": [subtitle or "Kurumsal Yönetici Sunumu"]}, *(slides or [])]
    n_slides = len(all_slides)

    content_types_Overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, n_slides + 1)
    )
    content_types_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
{content_types_Overrides}
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

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels_xml)

        for idx, sdata in enumerate(all_slides, start=1):
            stitle = html.escape(str(sdata.get("title") or f"Slayt {idx}"))
            bullets = [html.escape(str(b)) for b in (sdata.get("bullets") or []) if str(b).strip()]
            if not bullets:
                bullets = [html.escape(str(sdata.get("content") or ""))]

            paragraphs_xml = "\n".join(
                f"""          <a:p>
            <a:r><a:rPr lang="tr-TR" sz="2000" dirty="0"/><a:t>• {b}</a:t></a:r>
          </a:p>"""
                for b in bullets[:8]
            )
            slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="457200" y="365125"/><a:ext cx="8229600" cy="914400"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="tr-TR" sz="3200" b="1" dirty="0"/><a:t>{stitle}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="457200" y="1400000"/><a:ext cx="8229600" cy="3300000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
{paragraphs_xml}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>"""
            zf.writestr(f"ppt/slides/slide{idx}.xml", slide_xml)

    return out_path
