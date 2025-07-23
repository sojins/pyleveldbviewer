from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import tkinter as tk
from tkinter import PhotoImage
import ttkbootstrap as tb # -> from tkinter import ttk

from ui_utils import AutoScrollbar
from viewer_controller import init_controllers, select_log_dir, show_batch_page
from controller_state import state

def save_json_to_file(text_widget):
    import tkinter.filedialog as fd
    from tkinter import messagebox
    try:
        content = text_widget.get("1.0", "end-1c")
        if not content or len(content) == 0:
            return
    except:
        return

    # 저장할 위치와 파일 이름 선택
    file_path = fd.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        title="Save JSON to File"
    )

    if file_path:
        try:
            content = text_widget.get("1.0", "end-1c")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("성공", f"저장 완료: {file_path}")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 실패:\n{e}")
           
def create_ui(root:tb.Window):
    photo = PhotoImage(file=r'python_leveldb.png')
    root.wm_iconphoto(False, photo)
    # 상단 메뉴바 생성
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # ▶ 좌우 분할 PanedWindow
    main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief="raised")
    main_pane.pack(fill="both", expand=True)

    frame_opts = {"padding": 0, "borderwidth": 0, "relief": "flat"}

    # 왼쪽 패널 - TreeView + scrollbar
    left_frame = tb.Frame(main_pane, **frame_opts)

    # 내부 컨테이너 (TreeView + Scrollbar 묶음)
    tree_container = tb.Frame(left_frame, **frame_opts)
    tree_container.pack(fill="both", expand=True)
    
    # 수직 스크롤바
    tree_scrollbar = AutoScrollbar(tree_container, orient="vertical")

    tree = tb.Treeview(tree_container, 
                        style="Custom.Treeview",
                        show="tree",
                        yscrollcommand=tree_scrollbar.set)
    tree_scrollbar.config(command=tree.yview)

    # grid 배치 (scrollbar는 grid_remove/restore용)
    tree.grid(row=0, column=0, sticky="nsew")
    tree_scrollbar.grid(row=0, column=1, sticky="ns")
    tree_container.rowconfigure(0, weight=1)
    tree_container.columnconfigure(0, weight=1)

    # 전체 왼쪽 프레임을 PanedWindow에 추가
    main_pane.add(left_frame, minsize=150)  # 최소 너비 설정

    # 오른쪽 패널 - Notebook 등 기존 구성
    right_frame = tb.Frame(main_pane, **frame_opts)
    main_pane.add(right_frame)

    notebook = tb.Notebook(right_frame, bootstyle="primary", padding=0)
    notebook.pack(fill="both", expand=True)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)

    # 메뉴에 연결
    file_menu.add_command(label="Open Directory (for TreeView)", accelerator='Ctrl+T',
                            command=lambda: select_log_dir(param=tree))
    file_menu.add_separator()
    file_menu.add_command(label="종료", command=root.quit)

    ###############################################################
    # 👉 윗줄에 버튼을 담을 frame
    control_frame = tb.Frame(right_frame, **frame_opts)
    control_frame.pack(side="bottom", fill="x")
    
    # 저장 버튼
    save_button = tk.Button(control_frame, text="저장", command=lambda: save_json_to_file(json_view))
    save_button.pack(side="right", padx=10, pady=10)

    # control_frame 안에 추가
    state.prev_btn = prev_btn = tb.Button(control_frame, text="◀ 이전", command=lambda: show_batch_page("prev"))
    state.next_btn = next_btn = tb.Button(control_frame, text="다음 ▶", command=lambda: show_batch_page("next"))
    state.prev_btn["state"] = "disabled"
    state.next_btn["state"] = "disabled"
    prev_btn.pack(side="left", padx=10)
    next_btn.pack(side="left", padx=10)

    state.page_label = page_label = tb.Label(control_frame, text="Page: 1")
    page_label.pack(side="left", padx=1)
    ###############################################################
 
    # json frame - scrolled text
    json_frame = tb.Frame(notebook, **frame_opts)
    notebook.add(json_frame, text="JSON")
    
    json_view = ScrolledText(json_frame, font=("Consolas", 11), wrap="none", **frame_opts) # tk.Text(json_frame, font=("Consolas", 11), wrap="none", yscrollcommand=scrollbar.set)
    json_view.pack(side="left", expand=True, fill="both")

    # Progress bar
    progressbar = tb.Progressbar(right_frame, mode="indeterminate", bootstyle="info-striped")
    progressbar.pack(side="bottom", fill="x", padx=5, pady=3)
    progressbar.pack_forget()  # 초기에는 감추기

    init_controllers(tree, json_view, notebook, root, progressbar=progressbar)
    root.mainloop()
    