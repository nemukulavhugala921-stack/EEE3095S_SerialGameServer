import os
from PIL import Image, ImageDraw, ImageFont

def generate_fsm(output_path):
    width = 1400
    height = 680
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 22)
        font_state = ImageFont.truetype("arialbd.ttf", 18)
        font_sub = ImageFont.truetype("arial.ttf", 13)
        font_trans = ImageFont.truetype("consola.ttf", 13)
        font_trans_bd = ImageFont.truetype("consolab.ttf", 13)
        font_check = ImageFont.truetype("arialbd.ttf", 13)
        font_note = ImageFont.truetype("ariali.ttf", 12)
    except Exception:
        font_title = ImageFont.load_default()
        font_state = font_title
        font_sub = font_title
        font_trans = font_title
        font_trans_bd = font_title
        font_check = font_title
        font_note = font_title

    # Title
    draw.text((width // 2, 25), "STM32 Server Finite State Machine (FSM) & Move Validation Pipeline", fill="#0f172a", font=font_title, anchor="mm")

    # Main States
    # IDLE: (180, 240)
    # IN_PROGRESS: (640, 240)
    # GAME_OVER: (1160, 240)
    
    def draw_state(x, y, w, h, name, led_text, sub_text, bg_color, border_color):
        box = [x - w//2, y - h//2, x + w//2, y + h//2]
        draw.rounded_rectangle(box, radius=12, fill=bg_color, outline=border_color, width=3)
        draw.text((x, y - h//2 + 25), name, fill="#0f172a", font=font_state, anchor="mm")
        draw.line([(x - w//2 + 10, y - h//2 + 42), (x + w//2 - 10, y - h//2 + 42)], fill=border_color, width=1)
        draw.text((x, y - 5), led_text, fill="#334155", font=font_check, anchor="mm")
        draw.text((x, y + 20), sub_text, fill="#64748b", font=font_sub, anchor="mm")

    draw_state(160, 220, 220, 110, "IDLE", "LEDs: OFF (PB10, PB11)", "Awaiting NEW session", "#f1f5f9", "#475569")
    draw_state(640, 190, 260, 120, "IN_PROGRESS", "Turn LED: Red (X) / Green (O)", "Authoritative Active Match", "#eff6ff", "#2563eb")
    draw_state(1180, 220, 240, 110, "GAME_OVER", "LEDs: 5 Hz Blinker Active", "Match Terminated (Win/Draw)", "#fef2f2", "#dc2626")

    # Initial Power On
    draw.ellipse([20, 210, 40, 230], fill="#0f172a")
    draw.line([(40, 220), (50, 220)], fill="#0f172a", width=2)
    draw.polygon([(50, 220), (45, 216), (45, 224)], fill="#0f172a")
    draw.text((30, 195), "Reset / Boot", fill="#475569", font=font_note, anchor="mm")

    # Transition IDLE -> IN_PROGRESS: NEW
    draw.line([(270, 190), (510, 190)], fill="#1d4ed8", width=2)
    draw.polygon([(510, 190), (500, 185), (500, 195)], fill="#1d4ed8")
    draw.text((390, 175), "NEW / OK:BOARD:.........", fill="#1d4ed8", font=font_trans_bd, anchor="mm")
    draw.text((390, 205), "[Turn = Player X, Grid clear]", fill="#64748b", font=font_note, anchor="mm")

    # Transition IN_PROGRESS -> GAME_OVER: Win / Draw / Resign
    # Top curved arrow: Win / Draw
    draw.line([(770, 170), (1060, 190)], fill="#059669", width=2)
    draw.polygon([(1060, 190), (1050, 184), (1052, 194)], fill="#059669")
    draw.text((915, 155), "MOVE [3-in-a-row] / WIN:p", fill="#047857", font=font_trans_bd, anchor="mm")
    draw.text((915, 175), "MOVE [9 cells full] / DRAW", fill="#047857", font=font_trans_bd, anchor="mm")

    # Bottom straight arrow: Resign
    draw.line([(770, 220), (1060, 235)], fill="#d97706", width=2)
    draw.polygon([(1060, 235), (1050, 230), (1050, 240)], fill="#d97706")
    draw.text((915, 215), "RESIGN / OK:GAMEOVER", fill="#b45309", font=font_trans_bd, anchor="mm")

    # Transition GAME_OVER -> IN_PROGRESS: Replay NEW
    draw.arc([640, 80, 1180, 240], start=180, end=360, fill="#10b981", width=2)
    draw.polygon([(640, 130), (645, 120), (635, 120)], fill="#10b981")
    draw.text((910, 85), "NEW / OK:BOARD:......... (Replay match)", fill="#047857", font=font_trans_bd, anchor="mm")

    # Global Resets to IDLE: PA0 Button / CONNECT / DISCONNECT
    # Bottom long return line
    draw.line([(1180, 275), (1180, 360), (160, 360), (160, 275)], fill="#dc2626", width=2)
    draw.polygon([(160, 275), (155, 285), (165, 285)], fill="#dc2626")
    draw.text((640, 345), "SW0 Button Press (PA0)  OR  CONNECT / OK  OR  DISCONNECT / OK", fill="#b91c1c", font=font_trans_bd, anchor="mm")
    draw.text((640, 375), "[Hardware debounced 50ms; clears all game buffers and returns server to IDLE]", fill="#64748b", font=font_note, anchor="mm")

    # ==================== MOVE VALIDATION BRANCH (Sub-pipeline) ====================
    # Inside IN_PROGRESS, show validation flowchart box at the bottom
    val_box = [160, 420, 1240, 650]
    draw.rounded_rectangle(val_box, radius=10, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw.text((700, 440), "MOVE:p:i Validation Branch (Evaluated in strict order inside game_process_move())", fill="#0f172a", font=font_state, anchor="mm")

    # 4 Check Diamonds / Rectangles in a row
    checks = [
        {"x": 260, "name": "1. Format & State?", "fail_resp": "NACK:BADCMD / NACK:NOGAME", "desc": "Length <= 64, state==IN_PROGRESS"},
        {"x": 540, "name": "2. Range 0 <= i <= 8?", "fail_resp": "NACK:RANGE", "desc": "Integer cell index strictly 0 to 8"},
        {"x": 820, "name": "3. Correct Turn?", "fail_resp": "NACK:NOTURN", "desc": "Player letter matches active player"},
        {"x": 1100, "name": "4. Cell Empty?", "fail_resp": "NACK:OCCUPIED", "desc": "board[i] == '.' (not already X or O)"},
    ]

    for i, c in enumerate(checks):
        cx = c["x"]
        # Box for check
        draw.rounded_rectangle([cx - 100, 470, cx + 100, 525], radius=6, fill="#ffffff", outline="#2563eb", width=2)
        draw.text((cx, 488), c["name"], fill="#1e3a8a", font=font_check, anchor="mm")
        draw.text((cx, 508), c["desc"], fill="#64748b", font=font_sub, anchor="mm")

        # Down arrow: FAIL -> NACK
        draw.line([(cx, 525), (cx, 595)], fill="#dc2626", width=2)
        draw.polygon([(cx, 595), (cx - 5, 587), (cx + 5, 587)], fill="#dc2626")
        draw.text((cx, 550), "[No]", fill="#dc2626", font=font_check, anchor="rm")
        
        # NACK box
        draw.rounded_rectangle([cx - 95, 595, cx + 95, 630], radius=4, fill="#fef2f2", outline="#fca5a5", width=1)
        draw.text((cx, 612), c["fail_resp"], fill="#b91c1c", font=font_trans_bd, anchor="mm")

        # Right arrow to next check [Yes]
        if i < len(checks) - 1:
            next_x = checks[i+1]["x"]
            draw.line([(cx + 100, 497), (next_x - 100, 497)], fill="#059669", width=2)
            draw.polygon([(next_x - 100, 497), (next_x - 108, 492), (next_x - 108, 502)], fill="#059669")
            draw.text((cx + 115, 485), "[Yes]", fill="#047857", font=font_note)

    # From check 4 [Yes]: Update Board & Evaluate Outcome
    draw.arc([1100, 450, 1260, 500], start=270, end=360, fill="#059669", width=2)
    draw.line([(1260, 475), (1260, 390), (770, 390)], fill="#059669", width=2)
    draw.polygon([(770, 390), (780, 385), (780, 395)], fill="#059669")
    draw.text((1020, 405), "[All checks pass] -> Update board, swap turn, return OK:BOARD", fill="#047857", font=font_check, anchor="mm")

    img.save(output_path, "PNG", dpi=(150, 150))
    print(f"Saved FSM diagram to {output_path}")

def generate_gui_flowchart(output_path):
    width = 720
    height = 920
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 20)
        font_node = ImageFont.truetype("arialbd.ttf", 14)
        font_sub = ImageFont.truetype("arial.ttf", 12)
        font_mono = ImageFont.truetype("consolab.ttf", 13)
        font_note = ImageFont.truetype("ariali.ttf", 11)
    except Exception:
        font_title = ImageFont.load_default()
        font_node = font_title
        font_sub = font_title
        font_mono = font_title
        font_note = font_title

    draw.text((width // 2, 25), "Python Tkinter GUI Application Flowchart", fill="#0f172a", font=font_title, anchor="mm")

    # Helper for node
    def draw_node(x, y, w, h, title, sub, fill_c="#f8fafc", outline_c="#3b82f6", shape="rect"):
        box = [x - w//2, y - h//2, x + w//2, y + h//2]
        if shape == "oval":
            draw.rounded_rectangle(box, radius=20, fill=fill_c, outline=outline_c, width=2)
        elif shape == "diamond":
            draw.polygon([(x, y - h//2), (x + w//2, y), (x, y + h//2), (x - w//2, y)], fill=fill_c, outline=outline_c, width=2)
        else:
            draw.rounded_rectangle(box, radius=6, fill=fill_c, outline=outline_c, width=2)
        
        draw.text((x, y - 6 if sub else y), title, fill="#0f172a", font=font_node, anchor="mm")
        if sub:
            draw.text((x, y + 10), sub, fill="#475569", font=font_sub, anchor="mm")

    # Flowchart sequence
    # 1. Start
    draw_node(360, 70, 180, 40, "Launch GUI Client", "main.py initialization", "#eff6ff", "#2563eb", "oval")

    # Arrow down
    draw.line([(360, 90), (360, 130)], fill="#334155", width=2)
    draw.polygon([(360, 130), (356, 122), (364, 122)], fill="#334155")

    # 2. Connect Screen
    draw_node(360, 160, 300, 50, "Select COM Port & Connect", "Send CONNECT\\n via SerialDriver", "#f8fafc", "#64748b")

    draw.line([(360, 185), (360, 225)], fill="#334155", width=2)
    draw.polygon([(360, 225), (356, 217), (364, 217)], fill="#334155")

    # 3. Decision: Connected?
    draw_node(360, 260, 220, 60, "Response == OK?", "", "#fef9c3", "#ca8a04", "diamond")

    # Decision No: Error popup & retry
    draw.line([(470, 260), (580, 260), (580, 160), (510, 160)], fill="#dc2626", width=2)
    draw.polygon([(510, 160), (518, 156), (518, 164)], fill="#dc2626")
    draw.text((510, 248), "[No / Timeout]", fill="#dc2626", font=font_note)
    draw.text((585, 210), "Show error popup", fill="#b91c1c", font=font_note)

    # Decision Yes: Enable board & controls
    draw.line([(360, 290), (360, 335)], fill="#059669", width=2)
    draw.polygon([(360, 335), (356, 327), (364, 327)], fill="#059669")
    draw.text((365, 308), "[Yes]", fill="#047857", font=font_note)

    # 4. Ready State / Event Loop
    draw_node(360, 365, 340, 50, "Main Tkinter Event Loop", "Wait for Button Click (Move / New / Disconnect)", "#eff6ff", "#3b82f6")

    # Branches from User Input
    draw.line([(360, 390), (360, 440)], fill="#334155", width=2)
    draw.polygon([(360, 440), (356, 432), (364, 432)], fill="#334155")

    # 5. User clicks Cell -> Send MOVE:p:i
    draw_node(360, 470, 340, 50, "Player Clicks Board Cell (i)", "Transmit MOVE:<turn>:<i>\\n", "#f8fafc", "#64748b")

    draw.line([(360, 495), (360, 545)], fill="#334155", width=2)
    draw.polygon([(360, 545), (356, 537), (364, 537)], fill="#334155")

    # 6. Parse STM32 Authoritative Reply
    draw_node(360, 575, 260, 50, "Parse Server Reply", "Authoritative state dispatch", "#fef9c3", "#ca8a04", "diamond")

    # 3 reply branches:
    # A. OK:BOARD (Left)
    draw.line([(230, 575), (130, 575), (130, 650)], fill="#1d4ed8", width=2)
    draw.polygon([(130, 650), (126, 642), (134, 642)], fill="#1d4ed8")
    draw.text((150, 560), "OK:BOARD", fill="#1d4ed8", font=font_mono)
    draw_node(130, 680, 200, 50, "Update 3x3 Grid & Turn", "Redraw cells; swap turn display", "#eff6ff", "#3b82f6")

    # Loop back to Event Loop from OK:BOARD
    draw.line([(130, 705), (130, 770), (80, 770), (80, 365), (190, 365)], fill="#1d4ed8", width=2)
    draw.polygon([(190, 365), (182, 361), (182, 369)], fill="#1d4ed8")

    # B. NACK error (Center)
    draw.line([(360, 600), (360, 650)], fill="#dc2626", width=2)
    draw.polygon([(360, 650), (356, 642), (364, 642)], fill="#dc2626")
    draw.text((365, 622), "NACK:*", fill="#dc2626", font=font_mono)
    draw_node(360, 680, 200, 50, "Display Status Warning", "Keep board strictly unchanged", "#fef2f2", "#dc2626")

    # Loop back to Event Loop from NACK
    draw.line([(360, 705), (360, 770), (80, 770)], fill="#dc2626", width=2)

    # C. WIN:p / DRAW (Right)
    draw.line([(490, 575), (590, 575), (590, 650)], fill="#059669", width=2)
    draw.polygon([(590, 650), (586, 642), (594, 642)], fill="#059669")
    draw.text((515, 560), "WIN:* / DRAW", fill="#059669", font=font_mono)
    draw_node(590, 680, 200, 50, "Game Over Screen", "Disable board; show banner", "#ecfdf5", "#059669")

    # From Game Over -> Wait for New Game or Disconnect
    draw.line([(590, 705), (590, 770), (360, 770)], fill="#059669", width=2)

    # 7. Disconnect / Teardown (Bottom)
    draw_node(360, 830, 280, 44, "User Clicks Disconnect / Exit", "Send DISCONNECT\\n; close serial port", "#f1f5f9", "#475569")
    draw.line([(360, 770), (360, 808)], fill="#334155", width=2)
    draw.polygon([(360, 808), (356, 800), (364, 800)], fill="#334155")

    # End
    draw.line([(360, 852), (360, 880)], fill="#334155", width=2)
    draw.polygon([(360, 880), (356, 872), (364, 872)], fill="#334155")
    draw_node(360, 895, 120, 30, "Exit App", "", "#e2e8f0", "#64748b", "oval")

    img.save(output_path, "PNG", dpi=(150, 150))
    print(f"Saved GUI flowchart to {output_path}")

if __name__ == "__main__":
    out_dir = os.path.dirname(__file__)
    generate_fsm(os.path.join(out_dir, "fsm.png"))
    generate_gui_flowchart(os.path.join(out_dir, "gui.png"))
