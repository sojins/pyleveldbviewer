from threading import Thread
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tksheet import Sheet
from tkinter import filedialog
from data_util import normalize_row
from json_util import highlight_keys_fast, make_json_safe
from leveldb_wrapper import LevelDBWrapper

table_batch_dict = {}
ui = {}  # UI context 전역 dict

def init_controllers(tree_widget, json_widget, notebook_widget, root, progressbar):
    ui["tree"] = tree_widget
    ui["json_view"] = json_widget
    ui["notebook"] = notebook_widget
    ui["root"] = root
    ui["progressbar"] = progressbar
    # TreeView 이벤트 바인딩
    ui["tree"].bind("<<TreeviewSelect>>", on_select)

def on_cell_double_click(event):
    mt = event.widget  # sheet.MT (MainTable)
    sheet = mt.master  # Sheet 객체
    
    col = mt.identify_col(event)
    row = mt.identify_row(event)
    
    if row is None or col is None:
        return

    value = sheet.get_cell_data(row, col)
    show_cell_hex_popup(value, master=sheet.winfo_toplevel())

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
    popup = tk.Toplevel(master) if master else tk.Toplevel()
    popup.title("셀 상세 보기")
    popup.geometry("1300x600")

    # ▶ 좌우 분할 PanedWindow
    main_pane = ttk.PanedWindow(popup, orient=tk.HORIZONTAL)
    main_pane.pack(fill="both", expand=True)

    # ▶ 왼쪽 텍스트 영역
    text_frame = ttk.Frame(main_pane)
    text_scroll_y = tk.Scrollbar(text_frame, orient="vertical")
    text_box = tk.Text(text_frame, font=("Consolas", 11), wrap="word",
                       yscrollcommand=text_scroll_y.set)
    text_scroll_y.config(command=text_box.yview)
    text_scroll_y.pack(side="right", fill="y")
    text_box.pack(side="left", fill="both", expand=True)
    text_box.insert("1.0", str(content))
    text_box.config(state="disabled")
    main_pane.add(text_frame, weight=1)

    # ▶ 오른쪽 헥스 영역
    hex_frame = ttk.Frame(main_pane)
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
    ui['wrapper'] = wrapper
    tree = ui['tree']

    # TreeView 구성
    delete_all_nodes(tree)
    for db_name, tables in db.items():
        db_node = tree.insert("", "end", text=db_name)
        if isinstance(tables, dict):
            table_keys = tables.keys()
        else:
            table_keys = tables
        for table_name in table_keys:
            tree.insert(db_node, "end", text=f"{db_name}.{table_name}")
        
        # 폴더 경로 표시
        root_window = ui["root"]
        if root_window:
            root_window.title(f"LevelDB Viewer - {file_path}")
    remove_tabs()
    json_view = ui["json_view"]
    if json_view:
        json_view.delete("1.0", "end")       # 기존 내용 지우기

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
    progressbar = ui["progressbar"]
    progressbar.pack(side="bottom", fill="x", padx=5, pady=3)
    progressbar.start(10)

    def task():
        try:
            wrapper_obj = LevelDBWrapper()
            wrapper_obj.load_data_with_progress(progressbar, 
                                                file_path,
                                                callback=on_data_loaded) # lambda w, db: on_data_loaded(w, db, file_path))
        except:
            pass
        finally:
            progressbar.stop()
            progressbar.pack_forget()
    Thread(target=task).start()

def remove_tabs():
    '''
    # 기존 탭 모두 제거
    '''
    notebook = ui["notebook"]
    for tab_id in notebook.tabs():
        if tab_id.split('.')[-1] != '!frame':
            notebook.forget(tab_id)

def create_table_tab(schema: tuple, rows: list, index: int):
    notebook = ui["notebook"]
    # global notebook
    frame = tk.Frame(notebook)
    sheet = Sheet(frame, headers=list(schema))
    sheet.pack(fill="both", expand=True)

    sheet.enable_bindings((
        "single_select", "cell_select", "column_width_resize", "cell_double_click"
    ))

    table_data = [normalize_row(row, list(schema)) for row in rows]
    sheet.set_sheet_data(table_data)

    # 바인딩 등록
    sheet.bind("<Double-1>", on_cell_double_click)
    notebook.add(frame, text=f"Table-{index+1}")
    
                
# 선택 시 데이터 렌더링
def on_select(event): 
    tree = event.widget
    sel = tree.selection()
    if not sel:
        return
    
    wrapper = ui['wrapper']
    root = event.widget.master
    json_view = ui["json_view"]
    
    text = tree.item(sel[0], "text")
    if "." not in text:
        return
    
    # 로딩바 시작
    progressbar = ui["progressbar"]
    if progressbar:
        progressbar.pack(side="bottom", fill="x", padx=5, pady=3)
        progressbar.start(10)
    
    def task():
        try:
            db_name, table_name = text.split(".", 1)
            data = []
            create_first_gen = False

            # 1️⃣ 테이블 제너레이터 준비
            try:
                gen = view_table_new_cb(root, wrapper, db_name, table_name)
            except Exception as e:
                print(f"⚠️ Generation failed: {e}")
                return

            # 2️⃣ 배치 제너레이터 준비 (10개 단위)
            try:
                if _batch_gen is None or table_batch_dict.get(text) is None:
                    _batch_gen = LevelDBWrapper()._make_batch_gen(gen, 10)
                    table_batch_dict[text] = _batch_gen
                    create_first_gen = True
            except NameError:
                _batch_gen = LevelDBWrapper()._make_batch_gen(gen, 10)
                table_batch_dict[text] = _batch_gen
                create_first_gen = True

            # 3️⃣ 첫 배치 로드
            try:
                batch = next(_batch_gen)
            except StopIteration:
                if not create_first_gen:
                    try:
                        _batch_gen = LevelDBWrapper()._make_batch_gen(gen, 10)
                        table_batch_dict[text] = _batch_gen
                        batch = next(_batch_gen)
                    except StopIteration:
                        print("⚠️ No data!")
                        return
                else:
                    print("⚠️ No data!")
                    return

            # 4️⃣ 스키마별 그룹핑
            schema_groups = {}
            for item in batch:
                data.append(item)
                try:
                    schema = tuple(sorted(item.keys()))
                except Exception:
                    schema = ('',)
                schema_groups.setdefault(schema, []).append(item)

            # 5️⃣ 기존 탭 제거 후 새 탭 생성
            remove_tabs()
            for i, (schema, rows) in enumerate(schema_groups.items()):
                create_table_tab(schema, rows, i)

            # 6️⃣ JSON 뷰어 갱신
            pretty = make_json_safe(data)
            json_view.after(0, lambda: update_json_view(json_view, pretty))

        finally:
            # 7️ 로딩바 종료 (UI 스레드에서)
            progressbar.after(0, lambda: (
                progressbar.stop(),
                progressbar.pack_forget()
            ))


    def update_json_view(view, text):
        view.delete("1.0", "end")
        view.insert("1.0", text)
        highlight_keys_fast(view)

    Thread(target=task).start()
        
def view_table_new_cb(root, wrapper, db_name=None, table_name=None):
    if not db_name or not table_name:
        return
    
    # db = wrapper[db_name]
    obj_store = wrapper[db_name][table_name]  # accessing object store using name
    
    record_iter = obj_store.iterate_records(errors_to_stdout=True)
    batched_gen = (record.value for record in record_iter if record.value)
    return batched_gen
