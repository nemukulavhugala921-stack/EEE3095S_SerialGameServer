import os
import shutil
from PIL import Image, ImageDraw, ImageFont

def get_fonts():
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 15)
        font_bold = ImageFont.truetype("arialbd.ttf", 13)
        font_regular = ImageFont.truetype("arial.ttf", 12)
        font_small = ImageFont.truetype("arial.ttf", 11)
        font_italic = ImageFont.truetype("ariali.ttf", 11)
        font_mono = ImageFont.truetype("consola.ttf", 12)
        font_mono_bold = ImageFont.truetype("consolab.ttf", 12)
    except Exception:
        font_title = ImageFont.load_default()
        font_bold = font_title
        font_regular = font_title
        font_small = font_title
        font_italic = font_title
        font_mono = font_title
        font_mono_bold = font_title
    return {
        "title": font_title,
        "bold": font_bold,
        "regular": font_regular,
        "small": font_small,
        "italic": font_italic,
        "mono": font_mono,
        "mono_bold": font_mono_bold
    }

def render_ieee_sequence_diagram(output_path):
    f = get_fonts()
    width = 900
    height = 950
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    x_c = 170
    x_s = 730
    y_top = 40
    y_bot = 900

    def draw_actor(x, y, name, sub):
        bw, bh = 150, 42
        draw.rectangle([x - bw//2, y - bh//2, x + bw//2, y + bh//2], fill="#ffffff", outline="#000000", width=1)
        draw.text((x, y - 8), name, fill="#000000", font=f["bold"], anchor="mm")
        draw.text((x, y + 10), sub, fill="#444444", font=f["small"], anchor="mm")

    # Top & bottom actor boxes
    draw_actor(x_c, y_top, "Client (PC)", "Python GUI Client")
    draw_actor(x_s, y_top, "Server (STM32)", "Authoritative MCU")
    draw_actor(x_c, y_bot, "Client (PC)", "Python GUI Client")
    draw_actor(x_s, y_bot, "Server (STM32)", "Authoritative MCU")

    # Continuous clean dashed lifelines (IEEE Message Sequence Chart style)
    curr = y_top + 21
    while curr < y_bot - 21:
        draw.line([(x_c, curr), (x_c, min(curr + 6, y_bot - 21))], fill="#000000", width=1)
        draw.line([(x_s, curr), (x_s, min(curr + 6, y_bot - 21))], fill="#000000", width=1)
        curr += 12

    def draw_req(y, text, label=None):
        draw.line([(x_c, y), (x_s, y)], fill="#000000", width=1)
        draw.polygon([(x_s, y), (x_s - 9, y - 4), (x_s - 9, y + 4)], fill="#000000")
        draw.text((x_c + 15, y - 7), text, fill="#000000", font=f["mono_bold"], anchor="ls")
        if label:
            draw.text((x_c + 140, y - 7), f"[{label}]", fill="#444444", font=f["italic"], anchor="ls")

    def draw_resp(y, text, comment=None):
        curr_x = x_s
        while curr_x > x_c:
            draw.line([(curr_x, y), (max(curr_x - 6, x_c), y)], fill="#000000", width=1)
            curr_x -= 10
        draw.line([(x_c, y), (x_c + 8, y - 4)], fill="#000000", width=1)
        draw.line([(x_c, y), (x_c + 8, y + 4)], fill="#000000", width=1)
        draw.text((x_c + 15, y - 7), text, fill="#000000", font=f["mono_bold"], anchor="ls")
        if comment:
            draw.text((x_c + 200, y - 7), f"// {comment}", fill="#444444", font=f["italic"], anchor="ls")

    def draw_note(x, y, w, h, lines):
        ear = 8
        draw.polygon([(x, y), (x + w - ear, y), (x + w, y + ear), (x + w, y + h), (x, y + h)], fill="#ffffff", outline="#000000")
        draw.line([(x + w - ear, y), (x + w - ear, y + ear), (x + w, y + ear)], fill="#000000", width=1)
        for i, line in enumerate(lines):
            draw.text((x + 8, y + 5 + i * 14), line, fill="#000000", font=f["small"])

    # Transactions
    draw_req(100, "CONNECT\\n", "Link Handshake")
    draw_resp(130, "OK\\n", "State -> IDLE; buffers cleared")

    draw_req(180, "NEW\\n", "Start Match")
    draw_resp(210, "OK:BOARD:.........\\n", "State -> IN_PROGRESS, turn: X")

    draw_req(260, "MOVE:X:0\\n", "Player X claims cell 0")
    draw_resp(290, "OK:BOARD:X........\\n", "Move accepted; turn -> O")

    draw_req(350, "MOVE:X:1\\n", "Player X attempts out-of-turn play")
    draw_resp(380, "NACK:NOTURN\\n", "Rejected: board unchanged (X........)")

    draw_note(430, 395, 275, 38, [
        "Server Authority Guarantee:",
        "Illegal turn rejected; state untouched"
    ])
    draw.line([(430, 410), (370, 380)], fill="#666666", width=1)

    y_brk = 480
    draw.rectangle([x_c + 30, y_brk - 14, x_s - 30, y_brk + 14], fill="#fdfdfd", outline="#000000", width=1)
    draw.text((width // 2, y_brk), "- - - [ Intermediate valid play: O:3, X:1, O:4 ] - - -", fill="#222222", font=f["mono"], anchor="mm")

    draw_req(550, "MOVE:X:2\\n", "Player X completes row 0-1-2")
    draw_resp(580, "WIN:X\\n", "Match won; state -> GAME_OVER")

    draw_note(430, 595, 275, 38, [
        "Terminal Win Condition:",
        "Row 0-1-2 matched; LEDs blink at 5 Hz"
    ])
    draw.line([(430, 610), (370, 580)], fill="#666666", width=1)

    draw_req(680, "MOVE:O:5\\n", "Move attempt after game over")
    draw_resp(710, "NACK:NOGAME\\n", "Locked: no moves permitted in GAME_OVER")

    draw_req(780, "DISCONNECT\\n", "Session teardown")
    draw_resp(810, "OK\\n", "State -> IDLE; port closed")

    tmp = output_path + ".tmp.png"
    img.save(tmp, "PNG")
    shutil.move(tmp, output_path)
    print(f"Rendered clean sequence diagram: {output_path}")

if __name__ == "__main__":
    out_path = r"c:\Users\NEMUKULA VHUGALA\OneDrive - University of Cape Town\Desktop\3rd year\EEE3095S\EEE3096S_Project\docs\figures\sequence_diagram.png"
    render_ieee_sequence_diagram(out_path)
