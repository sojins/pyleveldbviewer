import ttkbootstrap as tb
from ui_layout import create_ui
from ui_style import apply_styles

if __name__ == "__main__":
    app = tb.Window()
    app.title("LevelDB Viewer")
    app.geometry("1300x600")
    apply_styles()  # 스타일 적용
    create_ui(app)
    app.mainloop()
