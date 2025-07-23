# ui_style.py
from ttkbootstrap import Style

def apply_styles():
    style = Style()
    style.theme_use("lumen") # "flatly"

    # TreeView 스타일 설정
    style.configure("Treeview",
        font=("Segoe UI", 11),
        rowheight=30,  # ✅ 줄 높이
        foreground="#333333",
        background="#ffffff",
        fieldbackground="#ffffff",
        bootstyle="info"
    )
    style.configure("Treeview.info",
                    rowheight=30,
                    font=("Segoe UI", 12)
                    )
    style.configure("Custom.Treeview",
                    rowheight=30,
                    font=("Segoe UI", 12),
                    relief='flat',
                    borderwidth=0
                    )

    style.map("Treeview",
        background=[("selected", "#007acc")],
        foreground=[("selected", "#ffffff")]
    )
