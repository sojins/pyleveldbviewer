import tkinter as tk
from tkinter import ttk

from viewer_controller import init_controllers, select_log_dir


notebook = None
root = None
g_wrapper = None


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
           
def create_ui(db_data='', gen=''):
    global tree
    root = tk.Tk()
    root.title("DB > Table Viewer with JSON Highlight")
    root.geometry("1000x600")

    # 상단 메뉴바 생성
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # ▶ 좌우 분할 PanedWindow
    main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief="raised")
    main_pane.pack(fill="both", expand=True)

    # 왼쪽 패널 - TreeView
    left_frame = ttk.Frame(main_pane, width=200)
    tree = ttk.Treeview(left_frame)
    tree.pack(fill="both", expand=True)
    main_pane.add(left_frame, minsize=150)  # 최소 너비 설정

    # 오른쪽 패널 - Notebook 등 기존 구성
    right_frame = ttk.Frame(main_pane)
    main_pane.add(right_frame)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    # 메뉴에 연결
    file_menu.add_command(label="Open Directory (for TreeView)", accelerator='Ctrl+T',
                            command=lambda: select_log_dir(param=tree))
    file_menu.add_separator()
    file_menu.add_command(label="종료", command=root.quit)

    ###############################################################
    # 👉 윗줄에 버튼을 담을 frame
    top_frame = tk.Frame(right_frame)
    top_frame.pack(side="top", fill="x")
    
    # 저장 버튼
    save_button = tk.Button(top_frame, text="저장", command=lambda: save_json_to_file(json_view))
    save_button.pack(side="right", padx=10, pady=5)
    ###############################################################

    notebook = ttk.Notebook(right_frame)
    notebook.pack(fill="both", expand=True)
    
    # json frame
    json_frame = tk.Frame(notebook)
    notebook.add(json_frame, text="JSON")
    
    # json frame - scrollbar
    scrollbar = tk.Scrollbar(json_frame)
    scrollbar.pack(side="right", fill="y")

    json_view = tk.Text(json_frame, font=("Consolas", 11), wrap="none", yscrollcommand=scrollbar.set)
    json_view.pack(side="left", expand=True, fill="both")
    scrollbar.config(command=json_view.yview)

    try:
        # TreeView 구성
        for db_name, tables in db_data.items():
            db_node = tree.insert("", "end", text=db_name)
            if isinstance(tables, dict):
                table_keys = tables.keys()
            else:
                table_keys = tables
            for table_name in table_keys:
                tree.insert(db_node, "end", text=f"{db_name}.{table_name}")
    except:
        pass

    init_controllers(tree, json_view, notebook)
    root.mainloop()
    