import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from tkinter import filedialog
from ttkbootstrap.scrolled import ScrolledText
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from constants import CHUNK_LINE_COUNT, LINE_WIDTH

theme = 'Dark'
def get_line_width_by_textview(scrolled_text:ScrolledText):
    scrolled_text.update_idletasks()  # 최신 크기 반영
    text_widget = scrolled_text  # 기본적으로 ScrolledText 자체가 Text 역할

    try:
        font_info = tkfont.Font(font=scrolled_text.cget("font"))
    except tk.TclError:
        font_info = tkfont.nametofont("TkDefaultFont")

    # 현재 위젯의 폭 (pixels)
    widget_width_px = scrolled_text.winfo_width()
    if widget_width_px <= 1:
            root = scrolled_text.master
            root.update_idletasks()
            widget_width_px = root.winfo_width()

    # 현재 사용 중인 폰트의 평균 문자 폭 (pixels)
    avg_char_width = font_info.measure("A")  # 'A'의 너비

    # 한 줄당 들어갈 수 있는 최대 문자 수
    line_width = max(LINE_WIDTH, widget_width_px // avg_char_width)

    return line_width

def show_large_cell_popup(content: str, master=None):
    if not isinstance(content, str):
        content = str(content)
    if not content: return    

    def render_chunk():
        start = current_start[0]
        end = min(start + CHUNK_LINE_COUNT, total_lines)
        chunk = lines[start:end]

        # TEXT 영역
        text_area.text.config(state="normal")
        text_area.delete("1.0", "end")
        text_area.insert("1.0", "\n".join(chunk))
        text_area.text.config(state="disabled")

        # HEX 영역
        try:
            if isinstance(chunk, bytes):
                byte_content = chunk
            else:
                chunk_str = ''.join(chunk)  # 리스트를 문자열로 병합
                byte_content = str(chunk_str).encode("utf-8", errors="replace")
                
            hex_area.config(state="normal")
            append_hex_line(hex_area, byte_content)
        except Exception as e:
            hex_area.insert("1.0", f"[헥스 변환 실패]\n{e}")
        finally:
            hex_area.config(state="disabled")


        # 상태 표시
        label.config(text=f"Lines {start+1}-{end} / {total_lines}")

    def append_hex_line(hex_area, byte_content):
        hex_area.delete("1.0", "end")

        for i in range(0, len(byte_content), 16):
            chunk = byte_content[i:i+16]
            offset_str = f"{i:08X}"
            hex_part = ' '.join(f"{b:02X}" for b in chunk)
            ascii_part = ''.join((chr(b) if 32 <= b < 127 else '.') for b in chunk)
            hex_area.insert("end", f"{offset_str}  ", "offset")
            hex_area.insert("end", f"{hex_part:<48}  ", "hex")
            hex_area.insert("end", ascii_part + "\n", "ascii")

        hex_area.insert("end", '\n')

    def next_chunk():
        if current_start[0] + CHUNK_LINE_COUNT < total_lines:
            current_start[0] += CHUNK_LINE_COUNT
            render_chunk()

    def prev_chunk():
        if current_start[0] > 0:
            current_start[0] = max(0, current_start[0] - CHUNK_LINE_COUNT)
            render_chunk()
    
    def save_current_view():
        start = current_start[0]
        end = min(start + CHUNK_LINE_COUNT, total_lines)
        chunk = lines[start:end]
        default_name = f"cell_data_lines_{start+1}_{end}.txt"

        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            initialfile=default_name,
                                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(chunk))

    # 팝업 창 UI
    popup = tk.Toplevel(master) if master else tk.Toplevel()
    popup.title("셀 상세 보기")
    popup.geometry("1400x600")

    frame = tk.Frame(popup)
    frame.pack(fill="both", expand=True)

    # 텍스트와 헥스 프레임
    text_frame = ttk.Frame(frame)
    hex_frame = ttk.Frame(frame, padding=0)

    text_frame.pack(side="left", fill="both", expand=True)
    hex_frame.pack(side="right", fill="both", expand=True)

    text_area = ScrolledText(text_frame, wrap="word", font=("Consolas", 11))
    text_area.pack(fill="both", expand=True)

    hex_scroll_y = tk.Scrollbar(hex_frame, orient="vertical")
    hex_scroll_x = tk.Scrollbar(hex_frame, orient="horizontal")
    hex_area = tk.Text(hex_frame, font=("Consolas", 11),
                    wrap="none",
                    yscrollcommand=hex_scroll_y.set,
                    xscrollcommand=hex_scroll_x.set)
    hex_scroll_y.config(command=hex_area.yview)
    hex_scroll_x.config(command=hex_area.xview)
    hex_scroll_y.pack(side="right", fill="y")
    hex_scroll_x.pack(side="bottom", fill="x")
    hex_area.pack(side="left", fill="both", expand=True)
    
    if theme == 'Dark':
        hex_area.config(bg="#1E1E1E", 
                        fg="#d4d4d4", 
                        insertbackground="#d4d4d4", # 커서 색
                        selectbackground="#264f78", # 선택 영역 배경 (Visual Studio 계열)
                        selectforeground="#ffffff"  # 선택 영역 글자 색
                        )

        hex_area.tag_configure("offset", foreground="#999999")
        hex_area.tag_configure("hex", foreground="#FFD700")
        hex_area.tag_configure("ascii", foreground="#00FF7F")
    else:
        hex_area.config(bg="white", fg="black", insertbackground="black")

        hex_area.tag_configure("offset", foreground="#888888")
        hex_area.tag_configure("hex", foreground="#1E90FF")
        hex_area.tag_configure("ascii", foreground="#228B22")



    # 하단 컨트롤
    control_frame = tk.Frame(popup)
    control_frame.pack(fill="x")

    prev_btn = tk.Button(control_frame, text="⟨ Prev", command=prev_chunk)
    next_btn = tk.Button(control_frame, text="Next ⟩", command=next_chunk)
    save_btn = tk.Button(control_frame, text="💾 Save", command=save_current_view)
    label = tk.Label(control_frame, text="")

    prev_btn.pack(side="left", padx=5, pady=4)
    next_btn.pack(side="left", padx=5, pady=4)
    save_btn.pack(side="left", padx=5, pady=4)
    label.pack(side="right", padx=10)

    # lines = content.splitlines()
    # total_lines = len(lines)
    # current_start = [0]  # 리스트로 감싸서 클로저 내부에서 갱신 가능

    line_width = get_line_width_by_textview(text_area)

    # 1줄로 된 긴 문자열 고려
    content = content.strip()
    lines = [content[i:i+line_width] for i in range(0, len(content), line_width)]
    total_lines = len(lines)
    current_start = [0]
    render_chunk()

if __name__ == "__main__":
    import ttkbootstrap as tb
    app = tb.Window()
    app.title("LevelDB Viewer")
    app.geometry("10x10")

    file_path = r"D:\Evidences\Windows\in\LevelDB202507\Slack\IndexedDB\244211.bin.json"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.readlines()
    show_large_cell_popup(content, master=app)
    app.mainloop()
