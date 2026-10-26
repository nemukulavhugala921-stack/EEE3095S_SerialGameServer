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

# ==============================================================================
# 1. IEEE UML SEQUENCE DIAGRAM
# ==============================================================================
def render_sequence_diagram(output_path):
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
        # Solid horizontal line from Client lifeline to Server lifeline
        draw.line([(x_c, y), (x_s, y)], fill="#000000", width=1)
        # Triangular filled arrowhead at server lifeline
        draw.polygon([(x_s, y), (x_s - 9, y - 4), (x_s - 9, y + 4)], fill="#000000")
        draw.text((x_c + 15, y - 7), text, fill="#000000", font=f["mono_bold"], anchor="ls")
        if label:
            draw.text((x_c + 140, y - 7), f"[{label}]", fill="#444444", font=f["italic"], anchor="ls")

    def draw_resp(y, text, comment=None):
        # Dashed horizontal line from Server lifeline to Client lifeline
        curr_x = x_s
        while curr_x > x_c:
            draw.line([(curr_x, y), (max(curr_x - 6, x_c), y)], fill="#000000", width=1)
            curr_x -= 10
        # Open arrowhead at client lifeline
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

# ==============================================================================
# 2. IEEE SERVER FSM & MOVE VALIDATION PIPELINE
# ==============================================================================
def render_fsm_diagram(output_path):
    f = get_fonts()
    width = 1200
    height = 740
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    # Standard UML State Box (rounded rect with compartment header and actions)
    def draw_uml_state(x, y, w, h, name, entries):
        draw.rounded_rectangle([x - w//2, y - h//2, x + w//2, y + h//2], radius=6, fill="#ffffff", outline="#000000", width=1)
        y_hdr = y - h//2 + 26
        draw.line([(x - w//2, y_hdr), (x + w//2, y_hdr)], fill="#000000", width=1)
        draw.text((x, y - h//2 + 13), name, fill="#000000", font=f["title"], anchor="mm")
        for i, text in enumerate(entries):
            draw.text((x - w//2 + 10, y_hdr + 8 + i * 16), text, fill="#333333", font=f["small"])

    # States: y = 175
    y_states = 175
    draw_uml_state(170, y_states, 200, 100, "IDLE", [
        "entry / g_board = .........",
        "entry / current_player = X",
        "entry / LEDs OFF (PB10, PB11)"
    ])

    draw_uml_state(600, y_states, 240, 100, "IN_PROGRESS", [
        "entry / Turn solid LED active",
        "        (PB10 for X, PB11 for O)",
        "do / evaluate move requests"
    ])

    draw_uml_state(1030, y_states, 220, 100, "GAME_OVER", [
        "entry / board locked",
        "entry / 5 Hz LED Blinker",
        "        (Winner LED or Both on Draw)"
    ])

    # Initial Power-on pseudo-state (black circle)
    draw.ellipse([20, y_states - 10, 40, y_states + 10], fill="#000000")
    draw.line([(40, y_states), (70, y_states)], fill="#000000", width=1)
    draw.polygon([(70, y_states), (62, y_states - 4), (62, y_states + 4)], fill="#000000")
    draw.text((30, y_states - 20), "Power On", fill="#000000", font=f["small"], anchor="mm")

    # Transition IDLE -> IN_PROGRESS: NEW
    draw.line([(270, y_states - 20), (480, y_states - 20)], fill="#000000", width=1)
    draw.polygon([(480, y_states - 20), (472, y_states - 24), (472, y_states - 16)], fill="#000000")
    draw.text((375, y_states - 35), "NEW / OK:BOARD:.........", fill="#000000", font=f["mono_bold"], anchor="mm")

    # Transition IN_PROGRESS -> GAME_OVER: Win / Draw / Resign
    # Win line
    draw.line([(720, y_states - 25), (920, y_states - 25)], fill="#000000", width=1)
    draw.polygon([(920, y_states - 25), (912, y_states - 29), (912, y_states - 21)], fill="#000000")
    draw.text((820, y_states - 40), "MOVE [3-in-a-row] / WIN:p", fill="#000000", font=f["mono_bold"], anchor="mm")

    # Draw & Resign line
    draw.line([(720, y_states + 25), (920, y_states + 25)], fill="#000000", width=1)
    draw.polygon([(920, y_states + 25), (912, y_states + 21), (912, y_states + 29)], fill="#000000")
    draw.text((820, y_states + 10), "MOVE [9 cells full] / DRAW", fill="#000000", font=f["mono_bold"], anchor="mm")
    draw.text((820, y_states + 40), "RESIGN / OK:GAMEOVER", fill="#000000", font=f["mono_bold"], anchor="mm")

    # Transition GAME_OVER -> IN_PROGRESS: NEW (Replay) - High Arc
    draw.arc([600, 40, 1030, 150], start=180, end=360, fill="#000000", width=1)
    draw.polygon([(600, 95), (605, 87), (595, 87)], fill="#000000")
    draw.text((815, 30), "NEW / OK:BOARD:......... (Replay)", fill="#000000", font=f["mono_bold"], anchor="mm")

    # Global Resets: SW0 button / CONNECT / DISCONNECT
    draw.line([(1030, y_states + 50), (1030, y_states + 110), (170, y_states + 110), (170, y_states + 50)], fill="#000000", width=1)
    draw.polygon([(170, y_states + 50), (166, y_states + 58), (174, y_states + 58)], fill="#000000")
    draw.text((600, y_states + 95), "SW0 Button Press (PA0)  OR  CONNECT / OK  OR  DISCONNECT / OK", fill="#000000", font=f["mono_bold"], anchor="mm")

    # ==================== MOVE VALIDATION BRANCH ====================
    y_box_top = 330
    draw.rectangle([50, y_box_top, 1150, 710], fill="#ffffff", outline="#000000", width=1)
    draw.text((width // 2, y_box_top + 18), "MOVE:p:i Validation Branch (Strict Evaluation Pipeline in game_process_move())", fill="#000000", font=f["title"], anchor="mm")

    stages = [
        {"x": 150, "name": "1. Format Valid?", "fail": "NACK:BADCMD"},
        {"x": 360, "name": "2. IN_PROGRESS?", "fail": "NACK:NOGAME"},
        {"x": 570, "name": "3. Index 0 <= i <= 8?", "fail": "NACK:RANGE"},
        {"x": 780, "name": "4. p == turn?", "fail": "NACK:NOTURN"},
        {"x": 990, "name": "5. board[i] == '.'?", "fail": "NACK:OCCUPIED"},
    ]

    def draw_decision_diamond(x, y, w, h, text):
        draw.polygon([(x, y - h//2), (x + w//2, y), (x, y + h//2), (x - w//2, y)], fill="#ffffff", outline="#000000", width=1)
        draw.text((x, y), text, fill="#000000", font=f["bold"], anchor="mm")

    y_dia = 425
    for i, st in enumerate(stages):
        cx = st["x"]
        draw_decision_diamond(cx, y_dia, 150, 56, st["name"])

        # Fail down arrow -> NACK
        draw.line([(cx, y_dia + 28), (cx, y_dia + 90)], fill="#000000", width=1)
        draw.polygon([(cx, y_dia + 90), (cx - 4, y_dia + 82), (cx + 4, y_dia + 82)], fill="#000000")
        draw.text((cx + 8, y_dia + 45), "[No]", fill="#000000", font=f["small"])

        # NACK box
        draw.rectangle([cx - 75, y_dia + 90, cx + 75, y_dia + 120], fill="#ffffff", outline="#000000", width=1)
        draw.text((cx, y_dia + 105), st["fail"], fill="#000000", font=f["mono_bold"], anchor="mm")

        # Pass right arrow
        if i < len(stages) - 1:
            next_x = stages[i+1]["x"]
            draw.line([(cx + 75, y_dia), (next_x - 75, y_dia)], fill="#000000", width=1)
            draw.polygon([(next_x - 75, y_dia), (next_x - 83, y_dia - 4), (next_x - 83, y_dia + 4)], fill="#000000")
            draw.text((cx + 82, y_dia - 12), "[Yes]", fill="#000000", font=f["small"])

    # Action & Evaluation Box
    y_box_top = 580
    y_box_bottom = 690
    x_box_left = 75
    x_box_right = 1040

    draw.rectangle([x_box_left, y_box_top, x_box_right, y_box_bottom], fill="#ffffff", outline="#000000", width=1)
    # Box title header
    draw.line([(x_box_left, y_box_top + 24), (x_box_right, y_box_top + 24)], fill="#000000", width=1)
    draw.text(((x_box_left + x_box_right)//2, y_box_top + 12), "State Mutation & Rule Evaluation (Executed Only After All 5 Guards Pass)", fill="#000000", font=f["bold"], anchor="mm")

    # Execution steps inside the box
    draw.text((x_box_left + 25, y_box_top + 32), "1. Commit Move to Memory:   g_board[idx] = player", fill="#000000", font=f["mono_bold"])
    draw.text((x_box_left + 25, y_box_top + 48), "2. Evaluate Win Condition:  check_win(player)  == true  ->  g_state = GAME_OVER; return WIN:<p>", fill="#000000", font=f["mono"])
    draw.text((x_box_left + 25, y_box_top + 64), "3. Evaluate Draw Condition: check_board_full() == true  ->  g_state = GAME_OVER; return DRAW", fill="#000000", font=f["mono"])
    draw.text((x_box_left + 25, y_box_top + 80), "4. Continue Match:          g_current_player = other(p); return OK:BOARD:<grid>", fill="#000000", font=f["mono"])

    # Stage 5 [Yes] -> Routes cleanly around the right side (x = 1110) completely clear of all NACK boxes
    cx5 = stages[4]["x"] # 990
    y_entry = (y_box_top + y_box_bottom) // 2 # 635

    # Path: from diamond 5 right tip (1065, 425) -> right to 1110 -> down to 635 -> left into box at 1040
    draw.line([(cx5 + 75, y_dia), (1110, y_dia), (1110, y_entry), (x_box_right, y_entry)], fill="#000000", width=1)
    # Arrowhead pointing left directly into the right wall of the box at (x_box_right, y_entry)
    draw.polygon([(x_box_right, y_entry), (x_box_right + 8, y_entry - 4), (x_box_right + 8, y_entry + 4)], fill="#000000")
    
    # Clean labels in the open right margin
    draw.text((1070, y_dia - 12), "[Yes]", fill="#000000", font=f["small"])
    draw.text((1115, (y_dia + y_entry)//2 - 8), "All 5", fill="#000000", font=f["small"])
    draw.text((1115, (y_dia + y_entry)//2 + 6), "Guards Pass", fill="#000000", font=f["small"])

    tmp = output_path + ".tmp.png"
    img.save(tmp, "PNG")
    shutil.move(tmp, output_path)
    print(f"Rendered clean FSM diagram: {output_path}")

# ==============================================================================
# 3. IEEE GUI FLOWCHART
# ==============================================================================
def render_gui_flowchart(output_path):
    f = get_fonts()
    width = 720
    height = 960
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    def draw_term(x, y, w, h, text):
        draw.rounded_rectangle([x - w//2, y - h//2, x + w//2, y + h//2], radius=h//2, fill="#ffffff", outline="#000000", width=1)
        draw.text((x, y), text, fill="#000000", font=f["bold"], anchor="mm")

    def draw_proc(x, y, w, h, title, sub=None):
        draw.rectangle([x - w//2, y - h//2, x + w//2, y + h//2], fill="#ffffff", outline="#000000", width=1)
        draw.text((x, y - 7 if sub else y), title, fill="#000000", font=f["bold"], anchor="mm")
        if sub:
            draw.text((x, y + 8), sub, fill="#444444", font=f["small"], anchor="mm")

    def draw_dia(x, y, w, h, text):
        draw.polygon([(x, y - h//2), (x + w//2, y), (x, y + h//2), (x - w//2, y)], fill="#ffffff", outline="#000000", width=1)
        draw.text((x, y), text, fill="#000000", font=f["bold"], anchor="mm")

    def draw_arrow_down(x, y0, y1, text=None):
        draw.line([(x, y0), (x, y1)], fill="#000000", width=1)
        draw.polygon([(x, y1), (x - 4, y1 - 8), (x + 4, y1 - 8)], fill="#000000")
        if text:
            draw.text((x + 6, (y0 + y1)//2), text, fill="#000000", font=f["small"])

    # 1. Start
    draw_term(360, 50, 160, 36, "Start GUI Client")
    draw_arrow_down(360, 68, 120)

    # 2. Port connect
    draw_proc(360, 140, 280, 44, "Select COM Port & Connect", "Send CONNECT\\n (115200 8N1)")
    draw_arrow_down(360, 162, 215)

    # 3. Decision Connected?
    draw_dia(360, 245, 180, 60, "Reply == OK?")

    draw.line([(450, 245), (560, 245), (560, 140), (500, 140)], fill="#000000", width=1)
    draw.polygon([(500, 140), (508, 136), (508, 144)], fill="#000000")
    draw.text((465, 230), "[No / Timeout]", fill="#000000", font=f["small"])
    draw.text((565, 190), "Show error dialog", fill="#444444", font=f["italic"])

    draw_arrow_down(360, 275, 340, "[Yes]")

    # 4. Main Event Loop
    draw_proc(360, 365, 320, 50, "Tkinter Main Event Loop", "Wait for user interaction (Move / New / Exit)")
    draw_arrow_down(360, 390, 450)

    # 5. User clicks square
    draw_proc(360, 475, 320, 46, "Player Clicks Board Square (i)", "Transmit MOVE:<p>:<i>\\n")
    draw_arrow_down(360, 498, 555)

    # 6. Parse response
    draw_dia(360, 585, 200, 60, "Server Response?")

    # A. OK:BOARD (Left column centered at x=150, w=160 -> left edge=70, right edge=230)
    draw.line([(260, 585), (150, 585), (150, 665)], fill="#000000", width=1)
    draw.polygon([(150, 665), (146, 657), (154, 657)], fill="#000000")
    draw.text((160, 570), "OK:BOARD", fill="#000000", font=f["mono"])
    draw_proc(150, 690, 160, 50, "Update 3x3 Grid", "Redraw cells; alternate turn")

    # B. NACK error (Center column centered at x=360, w=170)
    draw.line([(360, 615), (360, 665)], fill="#000000", width=1)
    draw.polygon([(360, 665), (356, 657), (364, 657)], fill="#000000")
    draw.text((368, 635), "NACK:*", fill="#000000", font=f["mono"])
    draw_proc(360, 690, 170, 50, "Show Status Warning", "Keep board strictly unchanged")

    # C. WIN / DRAW (Right column centered at x=570, w=170 -> left edge=485, right edge=655)
    draw.line([(460, 585), (570, 585), (570, 665)], fill="#000000", width=1)
    draw.polygon([(570, 665), (566, 657), (574, 657)], fill="#000000")
    draw.text((475, 570), "WIN:* / DRAW", fill="#000000", font=f["mono"])
    draw_proc(570, 690, 170, 50, "Game Over Announcement", "Lock all 9 buttons; show banner")

    # Return bus to Main Event Loop (x=25 is 45px clear to the left of Update 3x3 Grid)
    # Both OK:BOARD and NACK drop down to y=755 and join the bus to loop back
    draw.line([(150, 715), (150, 755), (25, 755), (25, 365), (200, 365)], fill="#000000", width=1)
    draw.polygon([(200, 365), (192, 361), (192, 369)], fill="#000000")
    draw.line([(360, 715), (360, 755), (150, 755)], fill="#000000", width=1)

    # From Game Over: [New Game] rejoins the bus; [Disconnect] proceeds to exit
    draw.line([(570, 715), (570, 755), (360, 755)], fill="#000000", width=1)
    draw.text((450, 742), "[New Game]", fill="#000000", font=f["small"])

    # Disconnect path from Game Over (or user window close)
    draw.line([(570, 755), (570, 795), (360, 795), (360, 818)], fill="#000000", width=1)
    draw.polygon([(360, 818), (356, 810), (364, 810)], fill="#000000")
    draw.text((575, 775), "[Close / Exit]", fill="#000000", font=f["small"])

    # 7. Disconnect
    draw_proc(360, 840, 280, 44, "User Clicks Disconnect / Closes Window", "Send DISCONNECT\\n; release COM port")
    draw_arrow_down(360, 862, 905)

    # 8. End
    draw_term(360, 920, 120, 32, "Exit")

    tmp = output_path + ".tmp.png"
    img.save(tmp, "PNG")
    shutil.move(tmp, output_path)
    print(f"Rendered clean GUI flowchart: {output_path}")

if __name__ == "__main__":
    out_dir = r"c:\Users\NEMUKULA VHUGALA\OneDrive - University of Cape Town\Desktop\3rd year\EEE3095S\EEE3096S_Project\docs\figures"
    render_sequence_diagram(os.path.join(out_dir, "sequence_diagram.png"))
    render_fsm_diagram(os.path.join(out_dir, "fsm.png"))
    render_gui_flowchart(os.path.join(out_dir, "gui.png"))
