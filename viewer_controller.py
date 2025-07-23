from threading import Thread
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from tksheet import Sheet
from ttkbootstrap.scrolled import ScrolledText

from data_util import normalize_row
from json_util import highlight_keys_fast, make_json_safe
from leveldb_wrapper import LevelDBWrapper, TableDataManager
from controller_state import table, ui, cell_full_data
from constants import PAGE_SIZE, CELL_TEXT_LIMIT



def init_controllers(tree_widget, json_widget, notebook_widget, root, progressbar):
    ui.tree = tree_widget
    ui.json_view = json_widget
    ui.notebook = notebook_widget
    ui.root = root
    ui.progressbar = progressbar

    # TreeView 이벤트 바인딩
    ui.tree.bind("<<TreeviewSelect>>", on_select)

def make_cell_summary(value, tab_index, row, col):
    if not isinstance(value, str):
        return value
    
    total_len = len(value)
    
    if total_len > CELL_TEXT_LIMIT:
        cell_full_data.setdefault(tab_index,{})[(row, col)] = value
        summary = value[:CELL_TEXT_LIMIT] + f"… (total: {total_len:,})"
        return (True, summary)
    
    return (False, value)

def render_table_page(sheet: Sheet, cols, rows, tab_index=1):
    ''' 현재 테이블 페이지를 렌더링 (요약 포함) '''
    sheet.headers(cols)
    cell_full_data.get(tab_index, {}).clear()

    summarized_rows = []
    summary_cells = []
    for row_idx, row in enumerate(rows):
        summarized_row = []
        for col_idx, cell in enumerate(row):
            (is_summary, summarized) = make_cell_summary(cell, tab_index, row_idx, col_idx)
            if is_summary:
                summary_cells.append((row_idx, col_idx))
            summarized_row.append(summarized)
        summarized_rows.append(summarized_row)

    sheet.set_sheet_data(summarized_rows)

    # 요약 셀은 글자색을 파란색 강조 적용
    if summary_cells:
        sheet.highlight_cells(cells=summary_cells, fg=("blue",))

def show_batch_page(direction: str):
    ''' 이전/다음 페이지 요청 처리  (TableDataManager 기반)'''
    key = table.current_key
    tdm = table.tdm_map.get(key)
    
    progressbar = ui.progressbar
    progressbar.pack(side="bottom", fill="x", padx=5, pady=3)
    progressbar.start(10)
    def task():
        try:
            table.prev_btn["state"] = "disabled"
            table.next_btn["state"] = "disabled"
            if not tdm:
                print(f"⚠️ TableDataManager not found for {key}")
                return
            
            if direction == "next":
                batch = tdm.get_next_page()
                if not batch:
                    print("Reached end of data")
                    return

            elif direction == "prev":
                batch = tdm.get_prev_page()
                if not batch:
                    print("At beginning")
                    return
        finally:
            update_table_and_json(batch)
            update_page_label()
            
            progressbar.stop()
            progressbar.pack_forget()
    Thread(target=task).start()

def update_table_and_json(batch):
    schema_groups = {}
    for item in batch:
        schema = tuple(sorted(item.keys())) if isinstance(item, dict) else ("",)
        schema_groups.setdefault(schema, []).append(item)
    remove_tabs_and_cache()
    for i, (schema, rows) in enumerate(schema_groups.items()):
        create_table_tab(schema, rows, i)

    json_view = ui.json_view
    json_view.delete("1.0", "end")
    json_view.insert("1.0", make_json_safe(batch))
    highlight_keys_fast(json_view)

def get_total_pages(tdm: TableDataManager):
    total_records = tdm.count_total()
    total_pages = (total_records + PAGE_SIZE - 1) // PAGE_SIZE  # 올림
    return total_pages

def update_page_label():
    key = table.current_key
    tdm = table.tdm_map.get(key)
    
    if not tdm:
        table.page_label.config(text="Page: - / -")
        return
    current = tdm.get_current_page_number()
    total_pages = tdm.count_total()
    per_page = tdm.batch_size
    max_page = (total_pages + per_page - 1) // per_page
    label = f"Page: {current} / {max_page}"
    table.page_label.config(text=label)

    # 버튼 상태 조정
    table.prev_btn["state"] = "normal" if current > 1 else "disabled"
    table.next_btn["state"] = "normal" if isinstance(total_pages, int) and current < max_page else "disabled"    

def on_cell_double_click(event):
    mt = event.widget  # sheet.MT (MainTable)
    sheet = mt.master  # Sheet 객체
    
    col = mt.identify_col(event)
    row = mt.identify_row(event)
    if row is None or col is None:
        return

    # notebook은 sheet의 부모의 부모
    notebook = sheet.master.master

    # 현재 탭의 index
    tab_index = notebook.index("current") - 1
    try:
        row_idx, col_idx = int(row), int(col)
        full_value = cell_full_data.get(tab_index, {}).get((row_idx, col_idx),"")

        if full_value:
            show_cell_hex_popup(full_value)
        else:
            # 요약 안 된 셀은 그대로 표시
            value = sheet.get_cell_data(row_idx, col_idx)
            show_cell_hex_popup(value)
    except Exception as e:
        print("Error in double click:", e)

def show_cell_popup(content, master=None):
    popup = tk.Toplevel(master) if master else tk.Toplevel()
    popup.title("셀 내용 보기")
    popup.geometry("400x300")

    text = tk.Text(popup, font=("Consolas", 11), wrap="word")
    text.insert("1.0", str(content))
    text.config(state="disabled")
    text.pack(fill="both", expand=True)

    btn = tk.Button(popup, text="닫기", command=popup.destroy)
    btn.pack(pady=5)

def show_cell_hex_popup(content, master=None):
    if not content: return
    popup = tk.Toplevel(master) if master else tk.Toplevel()
    popup.title("셀 상세 보기")
    popup.geometry("1300x600")

    # ▶ 좌우 분할 PanedWindow
    main_pane = ttk.PanedWindow(popup, orient=tk.HORIZONTAL)
    main_pane.pack(fill="both", expand=True)

    # ▶ 왼쪽 텍스트 영역
    text_frame = ttk.Frame(main_pane, padding=0)
    text_box = ScrolledText(text_frame, font=("Consolas", 11), wrap="word",)
    text_box.pack(side="left", fill="both", expand=True)
    text_box.insert("1.0", str(content))
    main_pane.add(text_frame, weight=1)

    # ▶ 오른쪽 헥스 영역
    hex_frame = ttk.Frame(main_pane, padding=0)
    hex_scroll_y = tk.Scrollbar(hex_frame, orient="vertical")
    hex_scroll_x = tk.Scrollbar(hex_frame, orient="horizontal")
    hex_box = tk.Text(hex_frame, font=("Consolas", 11),
                      wrap="none",
                      yscrollcommand=hex_scroll_y.set,
                      xscrollcommand=hex_scroll_x.set)
    hex_scroll_y.config(command=hex_box.yview)
    hex_scroll_x.config(command=hex_box.xview)
    hex_scroll_y.pack(side="right", fill="y")
    hex_scroll_x.pack(side="bottom", fill="x")
    hex_box.pack(side="left", fill="both", expand=True)

    try:
        if isinstance(content, bytes):
            byte_content = content
        else:
            byte_content = str(content).encode("utf-8", errors="replace")

        hex_lines = []
        for i in range(0, len(byte_content), 16):
            chunk = byte_content[i:i+16]
            hex_part = ' '.join(f"{b:02X}" for b in chunk)
            ascii_part = ''.join((chr(b) if 32 <= b < 127 else '.') for b in chunk)
            hex_lines.append(f"{i:08X}  {hex_part:<48}  {ascii_part}")
        hex_output = '\n'.join(hex_lines)

        hex_box.config(state="normal")
        hex_box.insert("1.0", hex_output)
        hex_box.config(state="disabled")
    except Exception as e:
        hex_box.insert("1.0", f"[헥스 변환 실패]\n{e}")

    main_pane.add(hex_frame, weight=1)

    # ▶ 하단 버튼
    btn_frame = ttk.Frame(popup)
    btn_frame.pack(fill="x", pady=5)

    def save_content():
        file_path = filedialog.asksaveasfilename(
            defaultextension=".bin",
            filetypes=[("Binary/Text Files", "*.bin *.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "wb") as f:
                    f.write(byte_content)
                messagebox.showinfo("성공", f"저장 완료:\n{file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패:\n{e}")

    tk.Button(btn_frame, text="내용 저장", command=save_content).pack(side="right", padx=10)
    tk.Button(btn_frame, text="닫기", command=popup.destroy).pack(side="right")

def delete_all_nodes(tree_obj):
    try:
        for i in tree_obj.get_children():
            tree_obj.delete(i)
    except:
        pass
    
def on_data_loaded(wrapper, db, file_path):
    ui.wrapper = wrapper
    tree = ui.tree

    # TreeView 구성
    delete_all_nodes(tree)
    
    tree.tag_configure("gray", foreground="gray")
    tree.tag_configure("db", foreground='#222', font=("Segoe UI", 11))
    tree.tag_configure("table", foreground='#666', font=("Segoe UI", 11))
    for db_name, tables in db.items():
        table_cnt = 0
        if isinstance(tables, dict):
            table_keys = tables.keys()
            table_cnt = len(table_keys)
        else:
            table_keys = tables
            table_cnt = len(table_keys)
        db_node = tree.insert("", "end", text=f"📁{db_name} ({table_cnt})", tags="db")
        for table_name in table_keys:
            # table인 경우 values에 이름 저장
            tdm = TableDataManager(wrapper, db_name, table_name)
            count = tdm.count_total()

            key = f"{db_name}.{table_name}"
            table.tdm_map[key] = tdm
            
            tag = "gray" if count == 0 else ""
            tree.insert(db_node, "end", text=f"📄 {table_name} ({count})", 
                        values=(db_name, table_name),
                        tags=(tag,"table") if tag else {})
        
        # 폴더 경로 표시
        root_window = ui.root
        if root_window:
            root_window.title(f"LevelDB Viewer - {file_path}")
    remove_tabs_and_cache()
    json_view = ui.json_view
    if json_view:
        json_view.delete("1.0", "end")       # 기존 내용 지우기
    update_page_label()

def select_log_dir(event=None, param=None):
    """
    :param event: event arg (not used)
    """
    tree = param
    file_path = filedialog.askdirectory(
        initialdir = '',
        title='Select IndexedDB Directory')
    
    if not file_path:
        return
    progressbar = ui.progressbar
    progressbar.pack(side="bottom", fill="x", padx=5, pady=3)
    progressbar.start(10)

    def task():
        try:
            wrapper_obj = LevelDBWrapper()
            wrapper_obj.load_data_with_progress(file_path,
                                                callback=on_data_loaded) # lambda w, db: on_data_loaded(w, db, file_path))
        except:
            pass
        finally:
            progressbar.stop()
            progressbar.pack_forget()
    Thread(target=task).start()

def remove_tabs_and_cache():
    ''' Sheet 형식으로 추가된 탭 모두 제거 '''
    notebook = ui.notebook
    for tab_id in notebook.tabs():
        if tab_id.split('.')[-1] != '!frame':
            notebook.forget(tab_id)
    cell_full_data.clear()

def create_table_tab(schema: tuple, rows: list, tab_index: int):
    notebook = ui.notebook
    frame = tk.Frame(notebook)
    sheet = Sheet(frame, headers=list(schema))
    sheet.pack(fill="both", expand=True)

    sheet.enable_bindings((
        "single_select", "cell_select", "column_width_resize", "cell_double_click"
    ))

    table_data = [normalize_row(row, list(schema)) for row in rows]
    render_table_page(sheet, cols=list(schema), rows=table_data, tab_index=tab_index)

    # 바인딩 등록
    sheet.bind("<Double-1>", on_cell_double_click)
    notebook.add(frame, text=f"Table-{tab_index+1}")
                
def on_select(event): 
    ''' Tree 선택 시 데이터 렌더링 '''
    tree = event.widget
    sel = tree.selection()
    if not sel:
        return
    
    json_view = ui.json_view
    
    try:
        db_name, table_name = tree.item(sel[0], "value")
    except ValueError:
        return

    # 로딩바 시작
    progressbar = ui.progressbar
    progressbar.pack(side="bottom", fill="x", padx=5, pady=3)
    progressbar.start(10)
    
    key = f"{db_name}.{table_name}"
    table.reset_if_key_changed(key)

    def task():
        try:
            tdm:TableDataManager = table.tdm_map.get(key)
            # 1️⃣ 첫 페이지 로드
            if tdm.is_first_page():
                batch = tdm.get_next_page()
                if not batch:
                    raise ValueError("⚠️ No data!")
            else:
                batch = tdm.get_current_page_data()
            
            # 2️⃣ 뷰 업데이트
            update_table_and_json(batch)
            update_page_label()
        except ValueError:
            print("⚠️ No data!")
            reset_view_tabs()
        finally:
            # 3️⃣ 로딩바 종료 (UI 스레드에서)
            progressbar.after(0, lambda: (
                progressbar.stop(),
                progressbar.pack_forget()
            ))

    def reset_view_tabs():
        ''' JSON 탭의 내용과 테이블 탭을 초기화 '''
        remove_tabs_and_cache()
        update_json_view(json_view, '')

    def update_json_view(view: ScrolledText, text):
        view.delete("1.0", "end")
        view.insert("1.0", text)
        highlight_keys_fast(view)

    Thread(target=task).start()
