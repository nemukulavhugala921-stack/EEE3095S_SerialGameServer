import os
from PIL import Image, ImageDraw, ImageFont

def create_compact_sequence_diagram(output_path):
    width = 960
    height = 840
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_header = ImageFont.truetype("arialbd.ttf", 16)
        font_sub = ImageFont.truetype("arial.ttf", 12)
        font_mono = ImageFont.truetype("consolab.ttf", 14)
        font_note = ImageFont.truetype("ariali.ttf", 12)
        font_bold = ImageFont.truetype("arialbd.ttf", 12)
    except Exception:
        font_header = ImageFont.load_default()
        font_sub = font_header
        font_mono = font_header
        font_note = font_header
        font_bold = font_header

    # Lifelines
    x_client = 190
    x_server = 740
    y_top = 40
    y_bottom = 790

    def draw_actor(x, y, title, subtitle, fill_c, border_c):
        bw, bh = 180, 44
        box = [x - bw//2, y - bh//2, x + bw//2, y + bh//2]
        draw.rounded_rectangle(box, radius=6, fill=fill_c, outline=border_c, width=2)
        draw.text((x, y - 8), title, fill="#0f172a", font=font_header, anchor="mm")
        draw.text((x, y + 10), subtitle, fill="#475569", font=font_sub, anchor="mm")

    # Top & Bottom Actors
    draw_actor(x_client, y_top, "Client (PC)", "Python GUI / Driver", "#eff6ff", "#3b82f6")
    draw_actor(x_server, y_top, "Server (STM32)", "Authoritative Referee", "#ecfdf5", "#10b981")
    draw_actor(x_client, y_bottom, "Client (PC)", "Python GUI", "#eff6ff", "#3b82f6")
    draw_actor(x_server, y_bottom, "Server (STM32)", "STM32F051", "#ecfdf5", "#10b981")

    # Lifeline Dashed
    curr = y_top + 22
    while curr < y_bottom - 22:
        draw.line([(x_client, curr), (x_client, min(curr + 6, y_bottom - 22))], fill="#cbd5e1", width=2)
        draw.line([(x_server, curr), (x_server, min(curr + 6, y_bottom - 22))], fill="#cbd5e1", width=2)
        curr += 12

    def draw_exchange(y_center, req_cmd, req_desc, resp_cmd, resp_desc, is_err=False, is_win=False):
        y_req = y_center - 18
        y_resp = y_center + 18
        margin = 12

        # 1. Request (Left to Right)
        x0 = x_client + margin
        x1 = x_server - margin
        req_color = "#1d4ed8"
        draw.line([(x0, y_req), (x1, y_req)], fill=req_color, width=2)
        draw.polygon([(x1, y_req), (x1 - 8, y_req - 4), (x1 - 8, y_req + 4)], fill=req_color)
        draw.text((x0 + 15, y_req - 6), req_cmd, fill=req_color, font=font_mono, anchor="ls")
        if req_desc:
            draw.text((x0 + 180, y_req - 6), f"({req_desc})", fill="#64748b", font=font_note, anchor="ls")

        # 2. Response (Right to Left)
        resp_color = "#dc2626" if is_err else ("#059669" if is_win else "#334155")
        curr_x = x1
        while curr_x > x0:
            draw.line([(curr_x, y_resp), (max(curr_x - 6, x0), y_resp)], fill=resp_color, width=2)
            curr_x -= 10
        draw.polygon([(x0, y_resp), (x0 + 8, y_resp - 4), (x0 + 8, y_resp + 4)], fill=resp_color)
        draw.text((x0 + 15, y_resp + 16), resp_cmd, fill=resp_color, font=font_mono, anchor="ls")
        if resp_desc:
            draw.text((x0 + 180, y_resp + 16), f"({resp_desc})", fill=resp_color if (is_err or is_win) else "#64748b", font=font_note, anchor="ls")

    # 1. CONNECT
    draw_exchange(115, "CONNECT\\n", "initial handshake", "OK\\n", "server enters IDLE state")

    # 2. NEW
    draw_exchange(205, "NEW\\n", "start new game session", "OK:BOARD:.........\\n", "state -> IN_PROGRESS, turn: Player X")

    # 3. Valid move
    draw_exchange(295, "MOVE:X:0\\n", "Player X takes cell 0", "OK:BOARD:X........\\n", "move accepted, turn -> Player O")

    # 4. Out-of-turn rejection
    draw_exchange(395, "MOVE:X:1\\n", "Player X attempts illegal consecutive move", "NACK:NOTURN\\n", "REJECTED: board unchanged (X........)", is_err=True)
    
    # Side badge for rejection
    draw.rounded_rectangle([x_server + 12, 370, width - 20, 420], radius=5, fill="#fef2f2", outline="#fca5a5", width=1)
    draw.text((x_server + 22, 384), "Turn Enforced", fill="#991b1b", font=font_bold)
    draw.text((x_server + 22, 401), "State untouched on error", fill="#b91c1c", font=font_note)

    # 5. Intermediate gameplay separator
    y_mid = 485
    draw.rounded_rectangle([x_client + 40, y_mid - 15, x_server - 40, y_mid + 15], radius=6, fill="#f8fafc", outline="#cbd5e1", width=1)
    draw.text((width // 2, y_mid), "... [ Intermediate gameplay: O:3, X:1, O:4 ] ...", fill="#475569", font=font_bold, anchor="mm")

    # 6. Winning Move
    draw_exchange(575, "MOVE:X:2\\n", "Player X completes row 0-1-2", "WIN:X\\n", "game over; board locks; LEDs blink", is_win=True)

    # Side badge for win
    draw.rounded_rectangle([x_server + 12, 550, width - 20, 600], radius=5, fill="#ecfdf5", outline="#86efac", width=1)
    draw.text((x_server + 22, 564), "Outcome Evaluated", fill="#065f46", font=font_bold)
    draw.text((x_server + 22, 581), "Authoritative referee logic", fill="#047857", font=font_note)

    # 7. Disconnect
    draw_exchange(675, "DISCONNECT\\n", "teardown connection", "OK\\n", "session closed, state -> IDLE")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", dpi=(150, 150))
    print(f"Saved compact sequence diagram to {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(__file__), "sequence_diagram.png")
    create_compact_sequence_diagram(out_file)
