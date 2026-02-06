# -*- coding: utf-8 -*-
"""
基金跟踪器 GUI 版本
使用 Tkinter 提供可视化界面
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
import threading
import sys
import subprocess
import os
import re


# =============================================================================
# 🎨 基金跟踪器 GUI
# =============================================================================
class FundTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📈 基金实时跟踪系统")
        self.root.geometry("1300x850")  # ✅ 增大窗口尺寸
        self.root.minsize(1200, 800)

        # 字体配置
        self.label_font = ("Microsoft YaHei UI", 10)
        self.button_font = ("Microsoft YaHei UI", 10, "bold")

        # 配置等宽字体
        self.setup_monospace_font()

        # 配色
        self.colors = {
            'success': '#27ae60',
            'warning': '#f39c12',
            'dark': '#2c3e50',
            'light': '#ecf0f1',
            'bg': '#f5f6fa',
            'border': '#95a5a6'
        }

        self.create_widgets()

    def setup_monospace_font(self):
        """设置等宽字体"""
        font_candidates = [
            ('Cascadia Mono', 10),
            ('Consolas', 10),
            ('Courier New', 10)
        ]

        for font_name, size in font_candidates:
            try:
                test_font = tkfont.Font(family=font_name, size=size)
                if test_font.measure('─') > 0:
                    self.mono_font = (font_name, size)
                    return
            except:
                continue

        self.mono_font = ('Courier New', 10)

    def create_widgets(self):
        # 主容器
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 配置区域
        config_outer = tk.Frame(main_container, bg="white", relief=tk.FLAT)
        config_outer.pack(fill=tk.X, pady=(0, 15))

        config_title = tk.Label(
            config_outer,
            text="⚙️ 配置参数",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white",
            fg=self.colors['dark'],
            anchor=tk.W
        )
        config_title.pack(fill=tk.X, padx=20, pady=(15, 10))

        tk.Frame(config_outer, height=1, bg="#e0e0e0").pack(fill=tk.X, padx=20)

        config_inner = tk.Frame(config_outer, bg="white")
        config_inner.pack(fill=tk.BOTH, padx=20, pady=15)

        # 左侧参数区
        params_frame = tk.Frame(config_inner, bg="white")
        params_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 第1行
        row1 = tk.Frame(params_frame, bg="white")
        row1.pack(fill=tk.X, pady=10)

        tk.Label(row1, text="连续上涨天数 ≥", font=self.label_font, bg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.up_days = ttk.Spinbox(row1, from_=1, to=10, width=5, font=self.label_font)
        self.up_days.set("2")
        self.up_days.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="或累计幅度 ≥", font=self.label_font, bg="white").pack(side=tk.LEFT, padx=(15, 8))
        self.up_pct = ttk.Spinbox(row1, from_=0.01, to=0.20, increment=0.01, width=7, font=self.label_font)
        self.up_pct.set("0.03")
        self.up_pct.pack(side=tk.LEFT, padx=5)

        # 第2行
        row2 = tk.Frame(params_frame, bg="white")
        row2.pack(fill=tk.X, pady=10)

        tk.Label(row2, text="连续下跌天数 ≥", font=self.label_font, bg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.down_days = ttk.Spinbox(row2, from_=1, to=10, width=5, font=self.label_font)
        self.down_days.set("3")
        self.down_days.pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="或累计幅度 ≥", font=self.label_font, bg="white").pack(side=tk.LEFT, padx=(15, 8))
        self.down_pct = ttk.Spinbox(row2, from_=0.01, to=0.20, increment=0.01, width=7, font=self.label_font)
        self.down_pct.set("0.03")
        self.down_pct.pack(side=tk.LEFT, padx=5)

        # 第3行
        row3 = tk.Frame(params_frame, bg="white")
        row3.pack(fill=tk.X, pady=10)

        tk.Label(row3, text="绘图模式:", font=self.label_font, bg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.plot_mode = ttk.Combobox(row3, values=["0-不绘图", "1-对比图", "2-子图"], width=10, font=self.label_font, state="readonly")
        self.plot_mode.current(0)
        self.plot_mode.pack(side=tk.LEFT, padx=5)

        tk.Label(row3, text="时间范围:", font=self.label_font, bg="white").pack(side=tk.LEFT, padx=(15, 8))
        self.plot_range = ttk.Combobox(row3, values=["1W", "1M", "3M", "6M", "1Y"], width=5, font=self.label_font, state="readonly")
        self.plot_range.current(2)
        self.plot_range.pack(side=tk.LEFT, padx=5)

        # 右侧按钮区
        button_container = tk.Frame(config_inner, bg="white")
        button_container.pack(side=tk.RIGHT, padx=(0, 50))

        btn_config = {
            'font': self.button_font,
            'fg': "white",
            'relief': tk.FLAT,
            'cursor': "hand2",
            'width': 11,
            'height': 1,
            'borderwidth': 0,
            'highlightthickness': 0
        }

        self.run_button = tk.Button(
            button_container,
            text="▶ 开始分析",
            bg=self.colors['success'],
            activebackground="#229954",
            command=self.run_analysis,
            **btn_config
        )
        self.run_button.pack(pady=(8, 20))

        clear_button = tk.Button(
            button_container,
            text="× 清空输出",
            bg=self.colors['border'],
            activebackground="#7f8c8d",
            command=self.clear_output,
            **btn_config
        )
        clear_button.pack(pady=(0, 8))

        # 运行日志区
        log_outer = tk.Frame(main_container, bg="white", relief=tk.FLAT)
        log_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        log_title = tk.Label(
            log_outer,
            text="📋 运行日志",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="white",
            fg=self.colors['dark'],
            anchor=tk.W
        )
        log_title.pack(fill=tk.X, padx=20, pady=(10, 10))

        tk.Frame(log_outer, height=1, bg="#e0e0e0").pack(fill=tk.X, padx=20)

        text_frame = tk.Frame(log_outer, bg="white")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        self.output_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.NONE,
            font=self.mono_font,
            bg="#fafafa",
            fg="#2c3e50",
            relief=tk.FLAT,
            padx=15,
            pady=15,
            borderwidth=0,
            highlightthickness=0,
            spacing1=0,
            spacing2=0,
            spacing3=0,
            tabs=tkfont.Font(font=self.mono_font).measure(' ' * 4)
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        status_bar = tk.Frame(self.root, bg=self.colors['light'], height=35)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            status_bar,
            text="💡 提示：修改参数后点击「开始分析」即可运行",
            font=("Microsoft YaHei UI", 9),
            bg=self.colors['light'],
            fg="#7f8c8d",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, padx=20, pady=8)

    def run_analysis(self):
        """运行分析"""
        self.run_button.config(
            state=tk.DISABLED,
            text="⏳ 运行中...",
            bg=self.colors['warning']
        )
        self.status_label.config(text="⏳ 正在分析，请稍候...")

        thread = threading.Thread(target=self.execute_fund_tracker)
        thread.daemon = True
        thread.start()

    def execute_fund_tracker(self):
        """执行fund_main.py"""
        try:
            cmd = [
                sys.executable,
                "fund_main.py",
                "--up_days", self.up_days.get(),
                "--up_pct", self.up_pct.get(),
                "--down_days", self.down_days.get(),
                "--down_pct", self.down_pct.get(),
                "--plot_mode", self.plot_mode.get()[0],
                "--plot_range", self.plot_range.get()
            ]

            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            env['COLUMNS'] = '120'
            env['LINES'] = '50'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            for line in iter(process.stdout.readline, ''):
                if line:
                    clean_line = self._strip_ansi(line)
                    self.output_text.insert(tk.END, clean_line)
                    self.output_text.see(tk.END)
                    self.root.update_idletasks()

            process.wait()

            if process.returncode == 0:
                self.status_label.config(text="✅ 分析完成！")
                self.output_text.insert(tk.END, "\n✅ 运行成功！\n")
            else:
                self.status_label.config(text="❌ 运行出错")
                self.output_text.insert(tk.END, "\n❌ 运行失败\n")

        except FileNotFoundError:
            messagebox.showerror("错误", "未找到 fund_main.py 文件！")
        except Exception as e:
            messagebox.showerror("错误", f"运行失败：{str(e)}")
        finally:
            self.run_button.config(
                state=tk.NORMAL,
                text="▶ 开始分析",
                bg=self.colors['success']
            )

    def _strip_ansi(self, text):
        """移除ANSI转义码"""
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b\[\?[0-9]+[hl]')
        return ansi_escape.sub('', text)

    def clear_output(self):
        """清空输出"""
        self.output_text.delete(1.0, tk.END)
        self.status_label.config(text="💡 提示：修改参数后点击「开始分析」即可运行")


# =============================================================================
# 🚀 主程序
# =============================================================================
if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root = tk.Tk()
    app = FundTrackerGUI(root)
    root.mainloop()
