import tkinter as tk
from tkinter import ttk
import json
import re
import os
from tkinter import filedialog
from tksheet import Sheet
from functools import partial
from ccl_chromium_reader import ccl_chromium_indexeddb

from json_util import make_cell_safe, make_json_safe, highlight_keys_fast
 
# TODO: list string 표시

# 샘플 DB 구조
sample_db = {
    "db1": {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ],
        "messages": [
            {"sender": "Alice", "text": "Hi"},
            {"sender": "Bob", "text": "Hello"}
        ]
    },
    "db2": {
        "logs": [
            {"timestamp": "2023-01-01", "action": "login"},
            {"timestamp": "2023-01-02", "action": "logout"}
        ]
    }
}

table_batch_dict = {}
def extract_table_data(json_data):
    if isinstance(json_data, list):
        if all(isinstance(row, dict) for row in json_data):
            columns = sorted({k for row in json_data for k in row})
            rows = [[row.get(col, "") for col in columns] for row in json_data]
            return columns, rows
        else:
            # list[str] / list[int] / list[float] 등
            columns = ["value"]
            # rows = [[str(item)] for item in json_data]
            rows = [[str(item)] for item in json_data]
            return columns, rows
    return [], []



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

def view_table_new_cb(root, wrapper, db_name=None, table_name=None):
    if not db_name or not table_name:
        return
    
    db = wrapper[db_name]
    obj_store = db[table_name]  # accessing object store using name
    
    record_iter = obj_store.iterate_records(errors_to_stdout=True)
    batched_gen = (record.value for record in record_iter if record.value)
    return batched_gen

def on_cell_double_click(event):
    global sheet
    row = sheet.get_currently_selected()[0]
    col = sheet.get_currently_selected()[1]
    value = sheet.get_cell_data(row, col)
    show_cell_popup(value)

def show_cell_popup(content):
    global root
    popup = tk.Toplevel(root)
    popup.title("셀 내용 보기")
    popup.geometry("400x300")

    text = tk.Text(popup, font=("Consolas", 11), wrap="word")
    text.insert("1.0", str(content))
    text.config(state="disabled")
    text.pack(fill="both", expand=True)

    btn = tk.Button(popup, text="닫기", command=popup.destroy)
    btn.pack(pady=5)

def make_double_click_handler(sheet_instance):
    def handler(event):
        row, col = sheet_instance.get_currently_selected()
        value = sheet_instance.get_cell_data(row, col)
        print(f"[Lambda 방식] {row}, {col}: {value}")
        value = sheet_instance.get_cell_data(row, col)
        show_cell_popup(value)
    return handler

def delete_all_nodes(tree_obj):
    for i in tree_obj.get_children():
        tree_obj.delete(i)

def select_log_dir(event=None, param=''):
    """
    :param event: event arg (not used)
    """
    global initial_dir, tree, g_wrapper
    file_path = filedialog.askdirectory(
        initialdir = initial_dir,
        title='Select IndexedDB Directory')
    (wrapper, db) = LevelDBWrapper().load(file_path)
    g_wrapper = wrapper
    try:
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
    except:
        pass

def normalize_row(row: dict, columns: list):
    return [make_cell_safe(row.get(col)) for col in columns]

def create_table_tab(schema: tuple, rows: list, index: int):
    global notebook
    frame = tk.Frame(notebook)
    new_sheet = Sheet(frame, headers=list(schema))
    new_sheet.pack(fill="both", expand=True)

    new_sheet.enable_bindings((
        "single_select", "cell_select", "column_width_resize", "cell_double_click"
    ))

    table_data = [normalize_row(row, list(schema)) for row in rows]
    new_sheet.set_sheet_data(table_data)

    notebook.add(frame, text=f"Table-{index+1}")

def _make_batch_gen(generator, batch_size=10):
        batch = []
        for item in generator:
            batch.append(item)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
    
# 선택 시 데이터 렌더링
def on_select(root, db_data, wrapper, event):
    global g_wrapper, _batch_gen
    if wrapper is None:
        wrapper = g_wrapper
    sel = tree.selection()
    if not sel:
        return
    text = tree.item(sel[0], "text")
    if "." not in text:
        return
    db_name, table_name = text.split(".", 1)
    create_first_gen = False
    batch = []
    try:
        data = db_data[db_name][table_name]
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
    except:
        gen = view_table_new_cb(root, wrapper, db_name, table_name)
        try:
            if _batch_gen is None or table_batch_dict.get(text) is None:
                table_batch_dict[text] = _batch_gen = _make_batch_gen(gen, 10)
                create_first_gen = True
        except NameError:
            table_batch_dict[text] = _batch_gen = _make_batch_gen(gen, 10)
            create_first_gen = True
        try:
            batch = next(_batch_gen)
        except StopIteration:
            try:
                if not create_first_gen:
                    table_batch_dict[text] = _batch_gen = _make_batch_gen(gen, 10)
                    batch = next(_batch_gen)
                else:
                    print("1")
            except:
                pass
        data = []
        # 📌 스키마별 그룹핑
        schema_groups = {}
        for item in batch:
            data.append(item)
            try:
                schema = tuple(sorted(item.keys())) # 스키마 식별자
            except:
                schema = ('')
            schema_groups.setdefault(schema, []).append(item)

        # 기존 탭 모두 제거
        for tab_id in notebook.tabs():
            if tab_id.split('.')[-1] != '!frame':
                notebook.forget(tab_id)
        
        # 그룹마다 새 탭 생성
        for i, (schema, rows) in enumerate(schema_groups.items()):
            create_table_tab(schema, rows, i)

        pretty = make_json_safe(data)

    # highlight_json(json_view, pretty)
    json_view.delete("1.0", "end")       # 기존 내용 지우기
    json_view.insert("1.0", pretty)
    highlight_keys_fast(json_view)
    
    cols, rows = extract_table_data(data)
    table_view.set_sheet_data(rows)
    if cols:
        table_view.headers(cols)

def create_ui(db_data, gen):
    global root, notebook, table_view, json_view, tree, sheet

    root = tk.Tk()
    root.title("DB > Table Viewer with JSON Highlight")
    root.geometry("1000x600")

    # 상단 메뉴바 생성
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    # 메뉴에 연결
    file_menu.add_command(label="Open Directory (for TreeView)", accelerator='Ctrl+T',
                            command=lambda: select_log_dir(param="tree"))
    file_menu.add_separator()
    file_menu.add_command(label="종료", command=root.quit)

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
    
    # table sheet
    table_view = Sheet(notebook)
    table_view.enable_bindings((
        "cell_double_click",
        "cell_select",
        "column_select",
        "column_width_resize",
        "edit_cell", 
        "row_select",         
        "single_select"))
    notebook.add(table_view, text="Table")
    # 바인딩 등록
    table_view.extra_bindings("cell_double_click", on_cell_double_click) #make_double_click_handler(table_view))
    sheet = table_view

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

    tree.bind("<<TreeviewSelect>>", partial(on_select, root, db_data, gen))
    root.mainloop()

class LevelDBWrapper:
    def find_indexeddb_components(self, selected_dir):
        # 마지막 폴더 이름이 'IndexedDB'인지 확인
        if os.path.basename(selected_dir) != "IndexedDB":
            return None

        # 하위 폴더 중 '.blob', '.leveldb'로 끝나는 폴더 찾기
        blob_path = None
        leveldb_path = None

        for entry in os.listdir(selected_dir):
            full_path = os.path.join(selected_dir, entry)
            if os.path.isdir(full_path):
                if entry.endswith(".blob"):
                    blob_path = full_path
                elif entry.endswith(".leveldb"):
                    leveldb_path = full_path

        if blob_path and leveldb_path:
            return blob_path, leveldb_path
        elif leveldb_path:
            return '', leveldb_path
        else:
            return None
        
    def load(self, base_dir):
        (blob_dir, db_dir) = self.find_indexeddb_components(base_dir)
        (wrapper, db_names) = self.load_data(db_dir=db_dir, blob_dir=blob_dir)

        return wrapper, db_names

    def load_data(self, db_dir, blob_dir):
        leveldb_folder_path = db_dir
        blob_folder_path = blob_dir
        db_names = []
        if not db_dir:
            return (None, db_names)

        # open the indexedDB:
        wrapper = ccl_chromium_indexeddb.WrappedIndexDB(leveldb_folder_path, blob_folder_path)
        dict_table = {}
        for name in wrapper._db_name_lookup:
            dict_table[f'{name[0]}'] = wrapper[name[0]]._obj_store_names
        return (wrapper, dict_table)

    def get_tables(self, db_name):
        try:
            tables = [item for item in self.data if item['name'] == db_name][0]['tables']
            return tables
        except:
            pass

if __name__ == "__main__":
    global initial_dir
    initial_dir = r'G:\Supports\25.07.16_TelegramWeb_LevelDB\Google_Chrome\IndexedDB'
    create_ui(db_data=None, gen=None)
