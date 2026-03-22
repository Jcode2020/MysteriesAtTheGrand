from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile


SLIDE_WIDTH = 12192000
SLIDE_HEIGHT = 6858000

PARCHMENT = "F3EADF"
LEDGER = "E9D8C0"
GUEST_PAPER = "FCF6EE"
AGED_GOLD = "B08A3E"
BURGUNDY = "6F2430"
PARLOR_GREEN = "31463A"
WALNUT_INK = "2D1D16"
WARM_TAUPE = "6F584B"
INFO_BLUE = "5E6F7B"
RULE_LINE = "D8CBBE"


def emu(inches: float) -> int:
    return int(round(inches * 914400))


def xml_text(value: str) -> str:
    return escape(value)


@dataclass
class TextRun:
    text: str
    size_pt: int
    color: str
    font_face: str
    bold: bool = False
    italic: bool = False
    uppercase: bool = False


def run_xml(run: TextRun) -> str:
    text = run.text.upper() if run.uppercase else run.text
    bold_attr = ' b="1"' if run.bold else ""
    italic_attr = ' i="1"' if run.italic else ""
    size = run.size_pt * 100
    return (
        f'<a:r>'
        f'<a:rPr lang="en-US" sz="{size}"{bold_attr}{italic_attr} dirty="0" smtClean="0">'
        f'<a:solidFill><a:srgbClr val="{run.color}"/></a:solidFill>'
        f'<a:latin typeface="{xml_text(run.font_face)}"/>'
        f'<a:ea typeface="{xml_text(run.font_face)}"/>'
        f'<a:cs typeface="{xml_text(run.font_face)}"/>'
        f"</a:rPr>"
        f"<a:t>{xml_text(text)}</a:t>"
        f"</a:r>"
    )


def paragraph_xml(runs: list[TextRun], *, align: str = "l") -> str:
    content = "".join(run_xml(run) for run in runs)
    end_size = runs[-1].size_pt * 100 if runs else 1800
    return (
        f'<a:p>'
        f'<a:pPr algn="{align}"/>'
        f"{content}"
        f'<a:endParaRPr lang="en-US" sz="{end_size}" dirty="0"/>'
        f"</a:p>"
    )


def textbox_xml(
    shape_id: int,
    name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    paragraphs: list[list[TextRun]],
    *,
    fill: str | None = None,
    line: str | None = None,
    line_width_pt: float = 1.0,
    inset_pt: int = 8,
    anchor: str = "t",
) -> str:
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else "<a:noFill/>"
    if line:
        line_width = int(round(line_width_pt * 12700))
        line_xml = f'<a:ln w="{line_width}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
    else:
        line_xml = "<a:ln><a:noFill/></a:ln>"
    body_xml = "".join(paragraph_xml(paragraph) for paragraph in paragraphs)
    inset = inset_pt * 12700
    return (
        f'<p:sp>'
        f'<p:nvSpPr>'
        f'<p:cNvPr id="{shape_id}" name="{xml_text(name)}"/>'
        f'<p:cNvSpPr txBox="1"/>'
        f'<p:nvPr/>'
        f'</p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'{fill_xml}'
        f'{line_xml}'
        f'</p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr wrap="square" anchor="{anchor}" lIns="{inset}" rIns="{inset}" tIns="{inset}" bIns="{inset}"/>'
        f'<a:lstStyle/>'
        f'{body_xml}'
        f'</p:txBody>'
        f'</p:sp>'
    )


def rect_xml(
    shape_id: int,
    name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    *,
    fill: str | None = None,
    line: str | None = None,
    line_width_pt: float = 1.0,
) -> str:
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else "<a:noFill/>"
    if line:
        line_width = int(round(line_width_pt * 12700))
        line_xml = f'<a:ln w="{line_width}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
    else:
        line_xml = "<a:ln><a:noFill/></a:ln>"
    return (
        f'<p:sp>'
        f'<p:nvSpPr>'
        f'<p:cNvPr id="{shape_id}" name="{xml_text(name)}"/>'
        f'<p:cNvSpPr/>'
        f'<p:nvPr/>'
        f'</p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'{fill_xml}'
        f'{line_xml}'
        f'</p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>'
        f'</p:sp>'
    )


def line_shape_xml(shape_id: int, name: str, x: int, y: int, cx: int, *, color: str, line_width_pt: float = 1.0) -> str:
    line_width = int(round(line_width_pt * 12700))
    return (
        f'<p:sp>'
        f'<p:nvSpPr>'
        f'<p:cNvPr id="{shape_id}" name="{xml_text(name)}"/>'
        f'<p:cNvSpPr/>'
        f'<p:nvPr/>'
        f'</p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="0"/></a:xfrm>'
        f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
        f'<a:ln w="{line_width}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:ln>'
        f'</p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>'
        f'</p:sp>'
    )


def base_slide_xml(name: str, shapes: list[str]) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="{xml_text(name)}">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {''.join(shapes)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
'''


def slide_rel_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
'''


def master_xml() -> str:
    frame_outer = rect_xml(2, "Outer Frame", emu(0.22), emu(0.22), emu(12.89), emu(7.06), line=RULE_LINE, line_width_pt=1.0)
    frame_inner = rect_xml(3, "Inner Frame", emu(0.34), emu(0.34), emu(12.65), emu(6.82), line=LEDGER, line_width_pt=0.7)
    top_rule = line_shape_xml(4, "Top Rule", emu(0.5), emu(0.95), emu(12.33), color=RULE_LINE, line_width_pt=0.7)
    bottom_rule = line_shape_xml(5, "Bottom Rule", emu(0.5), emu(6.95), emu(12.33), color=RULE_LINE, line_width_pt=0.7)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="Mysteries At The Grand Master">
    <p:bg>
      <p:bgPr>
        <a:solidFill><a:srgbClr val="{PARCHMENT}"/></a:solidFill>
        <a:effectLst/>
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {frame_outer}
      {frame_inner}
      {top_rule}
      {bottom_rule}
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="2147483649" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle>
      <a:lvl1pPr algn="l">
        <a:defRPr sz="3200" b="1">
          <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
          <a:latin typeface="Playfair Display"/>
        </a:defRPr>
      </a:lvl1pPr>
    </p:titleStyle>
    <p:bodyStyle>
      <a:lvl1pPr marL="0" indent="0">
        <a:defRPr sz="1800">
          <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
          <a:latin typeface="IBM Plex Mono"/>
        </a:defRPr>
      </a:lvl1pPr>
    </p:bodyStyle>
    <p:otherStyle>
      <a:defPPr/>
      <a:lvl1pPr marL="0" indent="0">
        <a:defRPr sz="1600">
          <a:solidFill><a:schemeClr val="tx1"/></a:solidFill>
          <a:latin typeface="IBM Plex Mono"/>
        </a:defRPr>
      </a:lvl1pPr>
    </p:otherStyle>
  </p:txStyles>
</p:sldMaster>
'''


def layout_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 type="blank" preserve="1" showMasterSp="1">
  <p:cSld name="Grand Template Blank">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
'''


def theme_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="MysteriesAtTheGrandTheme">
  <a:themeElements>
    <a:clrScheme name="GrandHotelPalette">
      <a:dk1><a:srgbClr val="{WALNUT_INK}"/></a:dk1>
      <a:lt1><a:srgbClr val="{GUEST_PAPER}"/></a:lt1>
      <a:dk2><a:srgbClr val="{WARM_TAUPE}"/></a:dk2>
      <a:lt2><a:srgbClr val="{LEDGER}"/></a:lt2>
      <a:accent1><a:srgbClr val="{AGED_GOLD}"/></a:accent1>
      <a:accent2><a:srgbClr val="{BURGUNDY}"/></a:accent2>
      <a:accent3><a:srgbClr val="{PARLOR_GREEN}"/></a:accent3>
      <a:accent4><a:srgbClr val="{PARCHMENT}"/></a:accent4>
      <a:accent5><a:srgbClr val="{WARM_TAUPE}"/></a:accent5>
      <a:accent6><a:srgbClr val="{INFO_BLUE}"/></a:accent6>
      <a:hlink><a:srgbClr val="{BURGUNDY}"/></a:hlink>
      <a:folHlink><a:srgbClr val="{PARLOR_GREEN}"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="GrandHotelType">
      <a:majorFont>
        <a:latin typeface="Playfair Display"/>
        <a:ea typeface="Playfair Display"/>
        <a:cs typeface="Playfair Display"/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface="IBM Plex Mono"/>
        <a:ea typeface="IBM Plex Mono"/>
        <a:cs typeface="IBM Plex Mono"/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="GrandHotelFormat">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
        <a:solidFill><a:schemeClr val="accent4"/></a:solidFill>
        <a:solidFill><a:schemeClr val="accent2"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="accent5"/></a:solidFill></a:ln>
        <a:ln w="19050"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln>
        <a:ln w="38100"><a:solidFill><a:schemeClr val="accent2"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="accent4"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt2"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>
'''


def content_types_xml(slide_count: int) -> str:
    slide_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for index in range(1, slide_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>
  <Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
{slide_overrides}
</Types>
'''


def root_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'''


def presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'    <p:sldId id="{255 + index}" r:id="rId{index + 1}"/>'
        for index in range(1, slide_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
{slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="{SLIDE_WIDTH}" cy="{SLIDE_HEIGHT}"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
'''


def presentation_rels_xml(slide_count: int) -> str:
    slide_relationships = "\n".join(
        f'  <Relationship Id="rId{index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{index}.xml"/>'
        for index in range(1, slide_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
{slide_relationships}
</Relationships>
'''


def master_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
'''


def app_xml(slide_count: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Cursor</Application>
  <PresentationFormat>Widescreen</PresentationFormat>
  <Slides>{slide_count}</Slides>
  <Notes>0</Notes>
  <HiddenSlides>0</HiddenSlides>
  <MMClips>0</MMClips>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Theme</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>1</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="1" baseType="lpstr">
      <vt:lpstr>Mysteries At The Grand Pitch Deck</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
  <Company></Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>1.0</AppVersion>
</Properties>
'''


def core_xml() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Mysteries At The Grand Pitch Deck</dc:title>
  <dc:creator>Cursor</dc:creator>
  <cp:lastModifiedBy>Cursor</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
'''


def pres_props_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentationPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>
'''


def view_props_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:viewPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 lastView="sldView">
  <p:normalViewPr>
    <p:restoredLeft sz="15620"/>
    <p:restoredTop sz="94660"/>
  </p:normalViewPr>
  <p:slideViewPr>
    <p:cSldViewPr snapToGrid="1" snapToObjects="1"/>
  </p:slideViewPr>
  <p:notesTextViewPr/>
  <p:gridSpacing cx="72008" cy="72008"/>
</p:viewPr>
'''


def footer_label_xml(shape_id: int, text: str) -> str:
    return textbox_xml(
        shape_id,
        "Footer Label",
        emu(11.85),
        emu(7.02),
        emu(0.95),
        emu(0.2),
        [[TextRun(text, 9, WARM_TAUPE, "IBM Plex Mono", uppercase=True)]],
        anchor="ctr",
    )


def market_problem_slide_xml() -> str:
    shapes = [
        textbox_xml(
            2,
            "Case Tab",
            emu(0.52),
            emu(0.34),
            emu(2.8),
            emu(0.34),
            [[TextRun("Slide 01 / Why Now", 10, WARM_TAUPE, "IBM Plex Mono", bold=True, uppercase=True)]],
            fill=LEDGER,
            line=RULE_LINE,
            line_width_pt=0.6,
            anchor="ctr",
        ),
        rect_xml(3, "Left Panel", emu(0.62), emu(1.0), emu(5.75), emu(5.1), fill=GUEST_PAPER, line=RULE_LINE, line_width_pt=0.8),
        rect_xml(4, "Right Panel", emu(6.54), emu(1.0), emu(5.96), emu(5.1), fill=LEDGER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            5,
            "Slide Title",
            emu(0.78),
            emu(1.18),
            emu(4.7),
            emu(0.78),
            [[TextRun("Luxury is shifting from objects to experiences.", 27, WALNUT_INK, "Playfair Display", italic=True)]],
        ),
        textbox_xml(
            6,
            "Who Label",
            emu(0.88),
            emu(2.28),
            emu(1.85),
            emu(0.26),
            [
                [TextRun("Consumer shift", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)],
            ],
        ),
        textbox_xml(
            7,
            "Who Body",
            emu(0.88),
            emu(2.66),
            emu(4.95),
            emu(0.92),
            [
                [TextRun("Bain says luxury consumers are prioritizing experiences over products.", 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("That trend maps directly into hospitality, where brands increasingly compete on atmosphere, story, and memory.", 14, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(8, "Accent Rule", emu(0.88), emu(3.76), emu(1.75), emu(0.03), fill=AGED_GOLD),
        textbox_xml(
            9,
            "Market Label",
            emu(0.88),
            emu(4.05),
            emu(1.9),
            emu(0.26),
            [
                [TextRun("Hospitality implication", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)],
            ],
        ),
        textbox_xml(
            10,
            "Market Body",
            emu(0.88),
            emu(4.42),
            emu(4.95),
            emu(1.18),
            [
                [TextRun("Premium and luxury hotels cannot only sell beds.", 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("They need an ownable experience that keeps the property top of mind before booking and between stays.", 14, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        textbox_xml(
            11,
            "Today Label",
            emu(6.82),
            emu(1.38),
            emu(2.6),
            emu(0.26),
            [[TextRun("Hospitality proof points", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            12,
            "Today Body",
            emu(6.82),
            emu(1.8),
            emu(5.35),
            emu(2.35),
            [
                [TextRun('Christoph Hoffmann / 25hours: "bevor wir uns hinsetzen und ein Hotel entwickeln, brauchen wir eine Geschichte."', 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun('And: "jedes Hotel muss seine eigene Geschichte haben."', 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("This is exactly the gap: hotels need a digital form for story-led immersion.", 14, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(13, "Pain Bar", emu(6.82), emu(4.34), emu(4.96), emu(0.45), fill=BURGUNDY),
        textbox_xml(
            14,
            "Pain Copy",
            emu(7.04),
            emu(4.42),
            emu(4.55),
            emu(0.22),
            [[TextRun("Hotels increasingly need experiences, not just rooms.", 10, GUEST_PAPER, "IBM Plex Mono", bold=True)]],
            anchor="ctr",
        ),
        textbox_xml(
            15,
            "Pain Notes",
            emu(6.82),
            emu(4.98),
            emu(5.2),
            emu(0.72),
            [
                [TextRun("Use a venn diagram here: luxury experiences x hospitality.", 13, WALNUT_INK, "Playfair Display", italic=True)],
            ],
        ),
        footer_label_xml(16, "Page 01"),
    ]
    return base_slide_xml("Why Now", shapes)


def solution_slide_xml() -> str:
    shapes = [
        textbox_xml(
            2,
            "Case Tab",
            emu(0.52),
            emu(0.34),
            emu(2.35),
            emu(0.34),
            [[TextRun("Slide 02 / Product Story", 10, WARM_TAUPE, "IBM Plex Mono", bold=True, uppercase=True)]],
            fill=LEDGER,
            line=RULE_LINE,
            line_width_pt=0.6,
            anchor="ctr",
        ),
        rect_xml(3, "Left Band", emu(0.62), emu(1.08), emu(3.55), emu(4.9), fill=BURGUNDY),
        textbox_xml(
            4,
            "Section Label",
            emu(0.95),
            emu(1.55),
            emu(2.2),
            emu(0.4),
            [[TextRun("Grand Hotel Pannonia", 12, GUEST_PAPER, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            5,
            "Section Title",
            emu(0.95),
            emu(2.1),
            emu(2.4),
            emu(1.9),
            [
                [TextRun("A customizable", 28, GUEST_PAPER, "Playfair Display", bold=True)],
                [TextRun("immersive hotel", 28, GUEST_PAPER, "Playfair Display", italic=True)],
                [TextRun("gaming experience", 24, GUEST_PAPER, "Playfair Display", italic=True)],
            ],
        ),
        textbox_xml(
            6,
            "Section Note",
            emu(0.95),
            emu(4.55),
            emu(2.35),
            emu(0.95),
            [[TextRun("Grand Hotel Pannonia turns a hotel's story, mood, and lore into a playable digital experience.", 11, GUEST_PAPER, "IBM Plex Mono")]],
        ),
        textbox_xml(
            7,
            "Main Title",
            emu(4.45),
            emu(1.48),
            emu(7.4),
            emu(1.2),
            [
                [TextRun("Customization can scale because the system is already built", 27, WALNUT_INK, "Playfair Display", italic=True)],
            ],
        ),
        rect_xml(8, "Card One", emu(4.46), emu(2.3), emu(2.35), emu(2.5), fill=GUEST_PAPER, line=RULE_LINE, line_width_pt=0.8),
        rect_xml(9, "Card Two", emu(6.96), emu(2.3), emu(2.35), emu(2.5), fill=GUEST_PAPER, line=RULE_LINE, line_width_pt=0.8),
        rect_xml(10, "Card Three", emu(9.46), emu(2.3), emu(2.35), emu(2.5), fill=GUEST_PAPER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            11,
            "Card One Text",
            emu(4.68),
            emu(2.58),
            emu(1.9),
            emu(1.95),
            [
                [TextRun("Immersive", 18, BURGUNDY, "Playfair Display", italic=True)],
                [TextRun("Guests do not just consume content. They enter a mystery world.", 13, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        textbox_xml(
            12,
            "Card Two Text",
            emu(7.18),
            emu(2.58),
            emu(1.9),
            emu(1.95),
            [
                [TextRun("Customizable", 18, BURGUNDY, "Playfair Display", italic=True)],
                [TextRun("Lore, visual identity, and atmosphere can be adapted to a specific hotel brand.", 13, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        textbox_xml(
            13,
            "Card Three Text",
            emu(9.68),
            emu(2.58),
            emu(1.9),
            emu(1.95),
            [
                [TextRun("Scalable", 18, BURGUNDY, "Playfair Display", italic=True)],
                [TextRun("Moodboards and the design system already live in code, so reskinning gets faster over time.", 13, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(14, "Bottom Rule", emu(4.46), emu(5.1), emu(2.2), emu(0.03), fill=AGED_GOLD),
        textbox_xml(
            15,
            "Prototype Line",
            emu(4.46),
            emu(5.28),
            emu(7.0),
            emu(0.52),
            [[TextRun("Show the current moodboard in the center and the previous ones around it to make customization tangible.", 12, PARLOR_GREEN, "IBM Plex Mono")]],
        ),
        footer_label_xml(16, "Page 02"),
    ]
    return base_slide_xml("Product Story", shapes)


def business_model_slide_xml() -> str:
    shapes = [
        textbox_xml(
            2,
            "Case Tab",
            emu(0.52),
            emu(0.34),
            emu(2.8),
            emu(0.34),
            [[TextRun("Slide 03 / Pricing + Market", 10, WARM_TAUPE, "IBM Plex Mono", bold=True, uppercase=True)]],
            fill=LEDGER,
            line=RULE_LINE,
            line_width_pt=0.6,
            anchor="ctr",
        ),
        textbox_xml(
            3,
            "Slide Title",
            emu(0.78),
            emu(1.16),
            emu(4.9),
            emu(0.7),
            [[TextRun("At EUR 10k customization, Europe alone is already a meaningful wedge.", 25, WALNUT_INK, "Playfair Display", italic=True)]],
        ),
        textbox_xml(
            4,
            "Slide Subtitle",
            emu(0.78),
            emu(1.72),
            emu(5.9),
            emu(0.35),
            [[TextRun("Storyline framing: lore + hotel identity customization first, recurring channels and app sales upside later.", 12, WARM_TAUPE, "IBM Plex Mono")]],
        ),
        rect_xml(5, "Main Panel", emu(0.78), emu(2.1), emu(4.05), emu(3.45), fill=GUEST_PAPER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            6,
            "Main Label",
            emu(1.0),
            emu(2.28),
            emu(2.2),
            emu(0.28),
            [[TextRun("What we charge", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            7,
            "Main Body",
            emu(1.0),
            emu(2.7),
            emu(3.55),
            emu(2.5),
            [
                [TextRun("EUR 10,000", 22, WALNUT_INK, "Playfair Display", bold=True)],
                [TextRun("for customization of lore and hotel identity.", 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("This is the one-time setup wedge used in the story.", 14, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(8, "Middle Panel", emu(5.06), emu(2.1), emu(3.1), emu(3.45), fill=LEDGER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            9,
            "Middle Label",
            emu(5.28),
            emu(2.28),
            emu(2.2),
            emu(0.28),
            [[TextRun("Europe wedge", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            10,
            "Middle Body",
            emu(5.28),
            emu(2.72),
            emu(2.6),
            emu(2.3),
            [
                [TextRun("Approx. EUR 400m+", 22, WALNUT_INK, "Playfair Display", bold=True)],
                [TextRun("using European premium + luxury hotels as the initial market frame.", 13, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("Use the waterfall chart here.", 13, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(11, "Side Panel", emu(8.4), emu(2.1), emu(3.82), emu(3.45), fill=GUEST_PAPER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            12,
            "Side Label",
            emu(8.62),
            emu(2.28),
            emu(2.3),
            emu(0.28),
            [[TextRun("Why this matters", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            13,
            "Side Body",
            emu(8.62),
            emu(2.72),
            emu(3.05),
            emu(2.28),
            [
                [TextRun("This does not yet include", 13, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("recurring revenue", 20, PARLOR_GREEN, "Playfair Display", bold=True)],
                [TextRun("from maintenance, seasonal stories, or traditional app sales channels.", 13, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        footer_label_xml(14, "Page 03"),
    ]
    return base_slide_xml("Pricing And Market", shapes)


def gtm_slide_xml() -> str:
    shapes = [
        textbox_xml(
            2,
            "Case Tab",
            emu(0.52),
            emu(0.34),
            emu(3.1),
            emu(0.34),
            [[TextRun("Slide 04 / Go-To-Market", 10, WARM_TAUPE, "IBM Plex Mono", bold=True, uppercase=True)]],
            fill=LEDGER,
            line=RULE_LINE,
            line_width_pt=0.6,
            anchor="ctr",
        ),
        textbox_xml(
            3,
            "Title",
            emu(0.78),
            emu(1.14),
            emu(6.1),
            emu(0.72),
            [[TextRun("Start with email outreach to hotel managers using the live prototype as proof.", 25, WALNUT_INK, "Playfair Display", italic=True)]],
        ),
        rect_xml(4, "Image Frame", emu(0.78), emu(1.95), emu(6.35), emu(3.95), fill=GUEST_PAPER, line=AGED_GOLD, line_width_pt=1.0),
        textbox_xml(
            5,
            "First Ten Label",
            emu(1.05),
            emu(2.18),
            emu(2.1),
            emu(0.28),
            [[TextRun("Outreach sequence", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            6,
            "First Ten Body",
            emu(1.05),
            emu(2.6),
            emu(5.55),
            emu(2.65),
            [
                [TextRun("1. Target hotel managers and marketing leads in premium and luxury properties.", 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("2. Lead with a short prototype case from the hackathon, not a long abstract pitch.", 14, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("3. Show a concrete outreach email on the slide to make the motion feel real.", 14, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(7, "Narrative Panel", emu(7.45), emu(1.95), emu(4.72), emu(3.95), fill=LEDGER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            8,
            "Narrative Label",
            emu(7.72),
            emu(2.18),
            emu(2.35),
            emu(0.28),
            [[TextRun("Why this channel works", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            9,
            "Narrative Text",
            emu(7.72),
            emu(2.64),
            emu(4.15),
            emu(2.4),
            [
                [TextRun("Hotel outreach is easier when the product already looks and feels like a finished guest experience.", 15, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("Customization is visible, so recipients can imagine their own property inside the same engine.", 15, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("The first wave is direct email; later waves can include agency and portfolio partnerships.", 15, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        rect_xml(10, "Quote Bar", emu(7.45), emu(5.2), emu(4.72), emu(0.42), fill=BURGUNDY),
        textbox_xml(
            11,
            "Quote Text",
            emu(7.62),
            emu(5.25),
            emu(4.35),
            emu(0.26),
            [[TextRun("Use a real outreach email here: short, visual, and prototype-led.", 10, GUEST_PAPER, "IBM Plex Mono", bold=True)]],
            anchor="ctr",
        ),
        footer_label_xml(12, "Page 04"),
    ]
    return base_slide_xml("Go To Market", shapes)


def demo_slide_xml() -> str:
    shapes = [
        textbox_xml(
            2,
            "Case Tab",
            emu(0.52),
            emu(0.34),
            emu(2.15),
            emu(0.34),
            [[TextRun("Slide 05 / Demo", 10, WARM_TAUPE, "IBM Plex Mono", bold=True, uppercase=True)]],
            fill=LEDGER,
            line=RULE_LINE,
            line_width_pt=0.6,
            anchor="ctr",
        ),
        textbox_xml(
            3,
            "Title",
            emu(0.78),
            emu(1.12),
            emu(6.3),
            emu(0.72),
            [[TextRun("Close with the live product: proof that the story already exists in playable form.", 23, WALNUT_INK, "Playfair Display", italic=True)]],
        ),
        textbox_xml(
            4,
            "Subtitle",
            emu(0.78),
            emu(1.68),
            emu(7.9),
            emu(0.38),
            [[TextRun("This final slide should feel like the invitation to enter the hotel, not a generic product recap.", 12, WARM_TAUPE, "IBM Plex Mono")]],
        ),
        rect_xml(5, "Demo Frame", emu(0.88), emu(2.12), emu(6.35), emu(3.45), fill=PARCHMENT, line=AGED_GOLD, line_width_pt=1.0),
        rect_xml(6, "Right Panel", emu(7.48), emu(2.12), emu(4.72), emu(3.45), fill=LEDGER, line=RULE_LINE, line_width_pt=0.8),
        textbox_xml(
            7,
            "Demo Placeholder",
            emu(1.42),
            emu(3.1),
            emu(5.75),
            emu(0.8),
            [
                [TextRun("Demo area", 24, WARM_TAUPE, "Playfair Display", italic=True)],
                [TextRun("Show the lobby, the concierge chat, and one visible room change.", 12, WARM_TAUPE, "IBM Plex Mono")],
            ],
            anchor="ctr",
        ),
        textbox_xml(
            8,
            "Right Label",
            emu(7.72),
            emu(2.34),
            emu(2.1),
            emu(0.28),
            [[TextRun("What to highlight", 10, BURGUNDY, "IBM Plex Mono", bold=True, uppercase=True)]],
        ),
        textbox_xml(
            9,
            "Right Body",
            emu(7.72),
            emu(2.78),
            emu(4.2),
            emu(2.2),
            [
                [TextRun("Historic luxury atmosphere", 15, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("AI-driven dialogue", 15, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("Customizable story world", 15, WARM_TAUPE, "IBM Plex Mono")],
                [TextRun("A digital experience hotels can actually own", 15, WARM_TAUPE, "IBM Plex Mono")],
            ],
        ),
        textbox_xml(
            10,
            "Close Line",
            emu(7.72),
            emu(5.0),
            emu(4.0),
            emu(0.4),
            [
                [TextRun("From one mystery to a portfolio of hotel experiences.", 16, WALNUT_INK, "Playfair Display", italic=True)],
            ],
        ),
        rect_xml(11, "Commitment Bar", emu(0.88), emu(5.02), emu(11.32), emu(0.42), fill=BURGUNDY),
        textbox_xml(
            12,
            "Commitment Text",
            emu(1.1),
            emu(5.09),
            emu(10.85),
            emu(0.24),
            [[TextRun("Demo of the app: show that Grand Hotel Pannonia already exists as a prototype, not just as a pitch idea.", 11, GUEST_PAPER, "IBM Plex Mono", bold=True)]],
            anchor="ctr",
        ),
        footer_label_xml(13, "Page 05"),
    ]
    return base_slide_xml("Demo", shapes)


def build_powerpoint(output_path: Path) -> None:
    slides = [
        market_problem_slide_xml(),
        solution_slide_xml(),
        business_model_slide_xml(),
        gtm_slide_xml(),
        demo_slide_xml(),
    ]

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(slides)))
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("docProps/app.xml", app_xml(len(slides)))
        archive.writestr("docProps/core.xml", core_xml())
        archive.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        archive.writestr("ppt/_rels/presentation.xml.rels", presentation_rels_xml(len(slides)))
        archive.writestr("ppt/presProps.xml", pres_props_xml())
        archive.writestr("ppt/viewProps.xml", view_props_xml())
        archive.writestr("ppt/theme/theme1.xml", theme_xml())
        archive.writestr("ppt/slideMasters/slideMaster1.xml", master_xml())
        archive.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels_xml())
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", layout_xml())

        for index, slide_xml in enumerate(slides, start=1):
            archive.writestr(f"ppt/slides/slide{index}.xml", slide_xml)
            archive.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", slide_rel_xml())


def main() -> None:
    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "mysteries_at_the_grand_pitch_deck.pptx"
    build_powerpoint(output_path)
    print(output_path)


if __name__ == "__main__":
    main()
