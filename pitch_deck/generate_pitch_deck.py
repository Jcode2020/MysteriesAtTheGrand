from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path


PAGE_WIDTH = 960
PAGE_HEIGHT = 540

PARCHMENT = "#F3EADF"
LEDGER = "#E9D8C0"
PAPER = "#FCF6EE"
GOLD = "#B08A3E"
BURGUNDY = "#6F2430"
GREEN = "#31463A"
INK = "#2D1D16"
TAUPE = "#6F584B"
RULE = "#D5C6B7"


def rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_text(text: str, max_width: float, font_size: float, width_factor: float) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) * font_size * width_factor <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


class PdfDocument:
    def __init__(self) -> None:
        self.objects: list[bytes | None] = [None]

    def reserve(self) -> int:
        self.objects.append(None)
        return len(self.objects) - 1

    def set_object(self, object_id: int, content: str | bytes) -> None:
        if isinstance(content, str):
            payload = content.encode("latin-1")
        else:
            payload = content
        self.objects[object_id] = payload

    def add_object(self, content: str | bytes) -> int:
        object_id = self.reserve()
        self.set_object(object_id, content)
        return object_id

    def add_stream(self, dictionary: dict[str, str | int], stream_data: bytes) -> int:
        dictionary_parts = [f"/{key} {value}" for key, value in dictionary.items()]
        dictionary_parts.append(f"/Length {len(stream_data)}")
        stream = (
            f"<< {' '.join(dictionary_parts)} >>\nstream\n".encode("latin-1")
            + stream_data
            + b"\nendstream"
        )
        return self.add_object(stream)

    def build(self, root_object_id: int) -> bytes:
        chunks = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
        offsets = [0]

        for object_id, payload in enumerate(self.objects[1:], start=1):
            if payload is None:
                raise ValueError(f"PDF object {object_id} was never set.")
            offsets.append(sum(len(chunk) for chunk in chunks))
            chunks.append(f"{object_id} 0 obj\n".encode("latin-1"))
            chunks.append(payload)
            chunks.append(b"\nendobj\n")

        xref_start = sum(len(chunk) for chunk in chunks)
        xref = [f"xref\n0 {len(self.objects)}\n".encode("latin-1"), b"0000000000 65535 f \n"]
        for offset in offsets[1:]:
            xref.append(f"{offset:010d} 00000 n \n".encode("latin-1"))

        trailer = (
            f"trailer\n<< /Size {len(self.objects)} /Root {root_object_id} 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode(
                "latin-1"
            )
        )
        return b"".join(chunks + xref + [trailer])


class Canvas:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def raw(self, command: str) -> None:
        self.commands.append(command)

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: str | None = None,
        stroke: str | None = None,
        line_width: float = 1,
    ) -> None:
        bits: list[str] = ["q"]
        if fill:
            r, g, b = rgb(fill)
            bits.append(f"{r:.4f} {g:.4f} {b:.4f} rg")
        if stroke:
            r, g, b = rgb(stroke)
            bits.append(f"{r:.4f} {g:.4f} {b:.4f} RG")
            bits.append(f"{line_width:.2f} w")
        bits.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re")
        if fill and stroke:
            bits.append("B")
        elif fill:
            bits.append("f")
        else:
            bits.append("S")
        bits.append("Q")
        self.raw("\n".join(bits))

    def line(self, x1: float, y1: float, x2: float, y2: float, *, stroke: str, line_width: float = 1) -> None:
        r, g, b = rgb(stroke)
        self.raw(
            "\n".join(
                [
                    "q",
                    f"{r:.4f} {g:.4f} {b:.4f} RG",
                    f"{line_width:.2f} w",
                    f"{x1:.2f} {y1:.2f} m",
                    f"{x2:.2f} {y2:.2f} l",
                    "S",
                    "Q",
                ]
            )
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        font: str,
        size: float,
        color: str = INK,
    ) -> None:
        r, g, b = rgb(color)
        self.raw(
            "\n".join(
                [
                    "BT",
                    f"/{font} {size:.2f} Tf",
                    f"{r:.4f} {g:.4f} {b:.4f} rg",
                    f"1 0 0 1 {x:.2f} {y:.2f} Tm",
                    f"({escape_pdf_text(value)}) Tj",
                    "ET",
                ]
            )
        )

    def multiline_text(
        self,
        x: float,
        y: float,
        lines: list[str],
        *,
        font: str,
        size: float,
        color: str = TAUPE,
        leading: float | None = None,
    ) -> None:
        if not lines:
            return
        r, g, b = rgb(color)
        actual_leading = leading or size * 1.45
        parts = [
            "BT",
            f"/{font} {size:.2f} Tf",
            f"{r:.4f} {g:.4f} {b:.4f} rg",
            f"{actual_leading:.2f} TL",
            f"1 0 0 1 {x:.2f} {y:.2f} Tm",
            f"({escape_pdf_text(lines[0])}) Tj",
        ]
        for line in lines[1:]:
            parts.append("T*")
            parts.append(f"({escape_pdf_text(line)}) Tj")
        parts.append("ET")
        self.raw("\n".join(parts))

    def image(self, x: float, y: float, width: float, height: float, image_name: str) -> None:
        self.raw(
            "\n".join(
                [
                    "q",
                    f"{width:.2f} 0 0 {height:.2f} {x:.2f} {y:.2f} cm",
                    f"/{image_name} Do",
                    "Q",
                ]
            )
        )

    def render(self) -> bytes:
        return "\n".join(self.commands).encode("latin-1")


def ensure_jpeg(source_png: Path, target_jpg: Path) -> Path:
    if target_jpg.exists() and target_jpg.stat().st_mtime >= source_png.stat().st_mtime:
        return target_jpg

    subprocess.run(
        ["sips", "-s", "format", "jpeg", str(source_png), "--out", str(target_jpg)],
        check=True,
        capture_output=True,
    )
    return target_jpg


def jpeg_dimensions(image_path: Path) -> tuple[int, int]:
    output = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(image_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    width_match = re.search(r"pixelWidth:\s+(\d+)", output)
    height_match = re.search(r"pixelHeight:\s+(\d+)", output)
    if not width_match or not height_match:
        raise ValueError(f"Could not determine image size for {image_path}")
    return int(width_match.group(1)), int(height_match.group(1))


def fit_box(box_width: float, box_height: float, image_width: int, image_height: int) -> tuple[float, float]:
    scale = min(box_width / image_width, box_height / image_height)
    return image_width * scale, image_height * scale


def draw_page_frame(canvas: Canvas, page_label: str, page_number: int) -> None:
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=PARCHMENT)
    canvas.rect(24, 24, PAGE_WIDTH - 48, PAGE_HEIGHT - 48, stroke=RULE, line_width=1.2)
    canvas.rect(34, 34, PAGE_WIDTH - 68, PAGE_HEIGHT - 68, stroke=LEDGER, line_width=0.8)
    canvas.rect(50, PAGE_HEIGHT - 74, 220, 26, fill=LEDGER, stroke=RULE, line_width=0.6)
    canvas.text(64, PAGE_HEIGHT - 58, page_label.upper(), font="FMono", size=11, color=TAUPE)
    canvas.text(PAGE_WIDTH - 118, 34, f"PAGE 0{page_number}", font="FMono", size=10, color=TAUPE)
    canvas.line(52, 78, PAGE_WIDTH - 52, 78, stroke=RULE, line_width=0.8)


def draw_title_page(canvas: Canvas, image_name: str, image_width: int, image_height: int) -> None:
    draw_page_frame(canvas, "Case File / Opening Statement", 1)
    canvas.rect(58, 104, 392, 352, fill=PAPER, stroke=RULE, line_width=0.9)
    canvas.rect(466, 104, 436, 352, fill=PAPER, stroke=RULE, line_width=0.9)
    canvas.rect(58, 420, 140, 22, fill=BURGUNDY)
    canvas.text(71, 427, "CONFIDENTIAL DEMO", font="FMono", size=10, color=PAPER)
    canvas.text(78, 382, "MYSTERIES", font="FTitleBold", size=34, color=INK)
    canvas.text(78, 338, "AT THE GRAND", font="FTitleBold", size=38, color=INK)
    canvas.text(80, 300, "Grand Pannonia Hotel", font="FTitleItalic", size=20, color=BURGUNDY)
    lines = wrap_text(
        "A short browser-based AI mystery where players chat with hotel characters, alter scenes in natural language, and solve an elegant Belle Epoque case.",
        318,
        13,
        0.56,
    )
    canvas.multiline_text(78, 254, lines, font="FMono", size=13, color=TAUPE, leading=20)
    canvas.line(78, 188, 218, 188, stroke=GOLD, line_width=2)
    canvas.text(78, 164, "LUXURY HOTEL DOSSIER", font="FMono", size=10, color=GREEN)
    canvas.text(78, 144, "IMMERSIVE CHAT + ROOM STATE", font="FMono", size=10, color=GREEN)
    canvas.text(78, 124, "DESKTOP-FIRST PROTOTYPE", font="FMono", size=10, color=GREEN)

    image_box_w, image_box_h = 400, 258
    draw_w, draw_h = fit_box(image_box_w, image_box_h, image_width, image_height)
    image_x = 484 + (image_box_w - draw_w) / 2
    image_y = 152 + (image_box_h - draw_h) / 2
    canvas.rect(484, 148, 400, 266, stroke=GOLD, line_width=1.2)
    canvas.image(image_x, image_y, draw_w, draw_h, image_name)
    canvas.text(486, 124, "Seeded lobby art from the live prototype", font="FMono", size=10, color=TAUPE)


def draw_opportunity_page(canvas: Canvas) -> None:
    draw_page_frame(canvas, "Why This Experience Matters", 2)
    canvas.text(64, 444, "A premium escape, not a complex game.", font="FTitleItalic", size=28, color=INK)
    canvas.text(64, 410, "The concept targets people who want atmosphere fast.", font="FMono", size=13, color=TAUPE)

    canvas.rect(62, 120, 278, 248, fill=PAPER, stroke=RULE, line_width=0.9)
    canvas.text(82, 340, "THE PLAYER", font="FMono", size=11, color=BURGUNDY)
    canvas.text(82, 312, "Karen, the time-poor luxury traveler", font="FTitleBold", size=18, color=INK)
    player_lines = wrap_text(
        "She wants a short atmospheric break that feels more like a private hotel indulgence than a demanding game session.",
        224,
        13,
        0.56,
    )
    canvas.multiline_text(82, 278, player_lines, font="FMono", size=13, color=TAUPE, leading=20)
    canvas.line(82, 208, 244, 208, stroke=GOLD, line_width=2)
    canvas.text(82, 184, "20-30 minute session", font="FMono", size=11, color=GREEN)
    canvas.text(82, 162, "Anonymous browser entry", font="FMono", size=11, color=GREEN)
    canvas.text(82, 140, "Designed for casual players", font="FMono", size=11, color=GREEN)

    canvas.rect(360, 120, 248, 248, fill=PAPER, stroke=RULE, line_width=0.9)
    canvas.text(380, 340, "THE NEED", font="FMono", size=11, color=BURGUNDY)
    need_lines = wrap_text(
        "Hospitality stories often live in brochures and static brand films. This turns the same world into something playable, conversational, and memorable.",
        194,
        13,
        0.56,
    )
    canvas.multiline_text(380, 304, need_lines, font="FMono", size=13, color=TAUPE, leading=20)
    canvas.text(380, 194, "Luxury first", font="FTitleBold", size=18, color=INK)
    canvas.text(380, 166, "Mystery in the details", font="FTitleBold", size=18, color=INK)
    canvas.text(380, 138, "No horror-game baggage", font="FTitleBold", size=18, color=INK)

    canvas.rect(628, 120, 270, 248, fill=LEDGER, stroke=RULE, line_width=0.9)
    canvas.text(648, 340, "POSITIONING", font="FMono", size=11, color=BURGUNDY)
    quote_lines = wrap_text(
        "An elegant browser mystery that can work as entertainment, a hotel world-building artifact, or a branded pre-stay invitation.",
        214,
        14,
        0.56,
    )
    canvas.multiline_text(648, 290, quote_lines, font="FTitleItalic", size=18, color=INK, leading=28)
    canvas.text(648, 154, "PROJECT VISION: immersive before game-like", font="FMono", size=10, color=TAUPE)


def draw_gameplay_page(canvas: Canvas, image_name: str, image_width: int, image_height: int) -> None:
    draw_page_frame(canvas, "Player Loop", 3)
    canvas.text(64, 442, "A mystery unfolds through chat, movement, and visual change.", font="FTitleItalic", size=28, color=INK)

    step_titles = [
        "1. Enter the hotel",
        "2. Question the world",
        "3. Alter the room",
        "4. Solve the case",
    ]
    step_bodies = [
        "Consent, opening theme, and a lobby arrival set the tone before the first turn.",
        "A concierge wire and in-world characters answer in concise natural language.",
        "Commands like inspect, move, open, or use trigger room-state updates and image edits when needed.",
        "The intended end state is a short, satisfying conclusion with clue review and scoring.",
    ]

    card_x_positions = [64, 286, 508, 730]
    for index, (title, body, x_pos) in enumerate(zip(step_titles, step_bodies, card_x_positions), start=1):
        canvas.rect(x_pos, 248, 166, 136, fill=PAPER if index % 2 else LEDGER, stroke=RULE, line_width=0.9)
        canvas.text(x_pos + 18, 352, title.upper(), font="FMono", size=10, color=BURGUNDY)
        body_lines = wrap_text(body, 128, 12, 0.56)
        canvas.multiline_text(x_pos + 18, 324, body_lines, font="FMono", size=12, color=TAUPE, leading=18)

    canvas.rect(64, 102, 832, 118, fill=PAPER, stroke=RULE, line_width=0.9)
    preview_w, preview_h = fit_box(220, 92, image_width, image_height)
    canvas.image(84, 115, preview_w, preview_h, image_name)
    canvas.line(326, 118, 326, 206, stroke=RULE, line_width=0.8)
    right_lines = wrap_text(
        "The current prototype already supports isolated anonymous sessions, room image loading, inventory retrieval, and streamed chat turns through the backend. That makes the loop feel alive even in early beta.",
        520,
        13,
        0.56,
    )
    canvas.text(346, 190, "CURRENT PROTOTYPE STATUS", font="FMono", size=11, color=BURGUNDY)
    canvas.multiline_text(346, 164, right_lines, font="FMono", size=13, color=TAUPE, leading=20)


def draw_features_page(canvas: Canvas) -> None:
    draw_page_frame(canvas, "Evidence Of Differentiation", 4)
    canvas.text(64, 444, "The product engine is more than a chatbot in costume.", font="FTitleItalic", size=28, color=INK)

    features = [
        (
            64,
            252,
            "SESSION ROOM STATES",
            "Each room can exist as versioned snapshots per anonymous visitor, which supports a personal timeline without breaking the shared base world.",
        ),
        (
            356,
            252,
            "AI-PLANNED ACTIONS",
            "Action-oriented turns are classified and routed through room logic rather than treated like plain flavor dialogue.",
        ),
        (
            648,
            252,
            "VISIBLE IMAGE CHANGES",
            "When a room truly changes, the backend can update the scene image so the world reflects what the player did.",
        ),
        (
            64,
            104,
            "SUITCASE INVENTORY",
            "Items are session-scoped and can be resolved from player phrasing, allowing clue play to feel tactile and legible.",
        ),
        (
            356,
            104,
            "STREAMED CONCIERGE WIRE",
            "Replies arrive as streamed text events, which keeps the interaction lightweight, modern, and responsive.",
        ),
        (
            648,
            104,
            "DESKTOP-FIRST DELIVERY",
            "The prototype favors legibility, atmosphere, and quiet luxury over cluttered game HUD patterns.",
        ),
    ]

    for x_pos, y_pos, title, body in features:
        canvas.rect(x_pos, y_pos, 248, 120, fill=PAPER, stroke=RULE, line_width=0.9)
        canvas.text(x_pos + 18, y_pos + 88, title, font="FMono", size=10, color=BURGUNDY)
        lines = wrap_text(body, 206, 12, 0.56)
        canvas.multiline_text(x_pos + 18, y_pos + 62, lines, font="FMono", size=12, color=TAUPE, leading=18)

    canvas.rect(64, 78, 832, 14, fill=GREEN)
    canvas.text(76, 82, "STACK: FLASK + REACT/VITE + SSE CHAT + OPENAI TEXT/IMAGE BACKEND", font="FMono", size=10, color=PAPER)


def draw_roadmap_page(canvas: Canvas) -> None:
    draw_page_frame(canvas, "Expansion Paths", 5)
    canvas.text(64, 444, "One hotel can become a whole portfolio of mysteries.", font="FTitleItalic", size=28, color=INK)

    canvas.rect(64, 118, 390, 266, fill=PAPER, stroke=RULE, line_width=0.9)
    canvas.text(86, 354, "ROADMAP", font="FMono", size=11, color=BURGUNDY)
    roadmap_items = [
        "Add a formal finale with clue submission and scoring.",
        "Expand from the lobby into more rooms and more suspects.",
        "Release seasonal or rotating mystery cases.",
        "Adapt the desktop-first experience for mobile after the core loop stabilizes.",
    ]
    y_cursor = 322
    for item in roadmap_items:
        canvas.rect(86, y_cursor - 6, 8, 8, fill=GOLD)
        lines = wrap_text(item, 320, 13, 0.56)
        canvas.multiline_text(104, y_cursor, lines, font="FMono", size=13, color=TAUPE, leading=20)
        y_cursor -= 56

    canvas.rect(488, 118, 408, 266, fill=LEDGER, stroke=RULE, line_width=0.9)
    canvas.text(510, 354, "USE CASES", font="FMono", size=11, color=BURGUNDY)
    use_case_lines = [
        "Premium entertainment demo for AI storytelling.",
        "Hospitality brand activation or pre-stay invitation.",
        "Seasonal marketing campaign built around a hotel world.",
        "Expandable framework for multiple locations and recurring stories.",
    ]
    y_cursor = 322
    for item in use_case_lines:
        canvas.text(510, y_cursor, "+", font="FTitleBold", size=18, color=GREEN)
        lines = wrap_text(item, 320, 13, 0.56)
        canvas.multiline_text(530, y_cursor, lines, font="FMono", size=13, color=TAUPE, leading=20)
        y_cursor -= 56

    canvas.rect(64, 80, 832, 24, fill=BURGUNDY)
    canvas.text(
        78,
        87,
        "MYSTERIES AT THE GRAND | A quiet luxury mystery built for memorable short-form immersion.",
        font="FMono",
        size=10,
        color=PAPER,
    )


def build_pitch_deck(output_path: Path, image_path: Path) -> None:
    lobby_jpeg = ensure_jpeg(image_path, output_path.with_name("lobby_reference.jpg"))
    lobby_width, lobby_height = jpeg_dimensions(lobby_jpeg)
    lobby_bytes = lobby_jpeg.read_bytes()

    document = PdfDocument()

    title_font_id = document.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>")
    italic_font_id = document.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic >>")
    mono_font_id = document.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    image_id = document.add_stream(
        {
            "Type": "/XObject",
            "Subtype": "/Image",
            "Width": lobby_width,
            "Height": lobby_height,
            "ColorSpace": "/DeviceRGB",
            "BitsPerComponent": 8,
            "Filter": "/DCTDecode",
        },
        lobby_bytes,
    )

    resources_id = document.reserve()
    page_ids = [document.reserve() for _ in range(5)]
    pages_id = document.reserve()

    pages: list[bytes] = []
    for drawer in (
        lambda canvas: draw_title_page(canvas, "ImLobby", lobby_width, lobby_height),
        draw_opportunity_page,
        lambda canvas: draw_gameplay_page(canvas, "ImLobby", lobby_width, lobby_height),
        draw_features_page,
        draw_roadmap_page,
    ):
        canvas = Canvas()
        drawer(canvas)
        pages.append(canvas.render())

    content_ids = [document.add_stream({}, page_bytes) for page_bytes in pages]

    document.set_object(
        resources_id,
        (
            f"<< /Font << /FTitleBold {title_font_id} 0 R /FTitleItalic {italic_font_id} 0 R /FMono {mono_font_id} 0 R >> "
            f"/XObject << /ImLobby {image_id} 0 R >> >>"
        ),
    )

    for page_id, content_id in zip(page_ids, content_ids):
        document.set_object(
            page_id,
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources {resources_id} 0 R /Contents {content_id} 0 R >>"
            ),
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    document.set_object(pages_id, f"<< /Type /Pages /Count {len(page_ids)} /Kids [ {kids} ] >>")
    catalog_id = document.add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    output_path.write_bytes(document.build(catalog_id))


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = project_root / "backend" / "seed" / "persistent" / "images" / "lobby.png"
    output_path = output_dir / "mysteries_at_the_grand_pitch_deck.pdf"
    build_pitch_deck(output_path, image_path)
    print(output_path)


if __name__ == "__main__":
    main()
