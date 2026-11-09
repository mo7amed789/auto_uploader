"""
Instagram Auto-Uploader Desktop GUI
واجهة سطح المكتب التفاعلية لرفع الفيديوهات إلى إنستغرام تلقائياً
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from uploader_engine import InstagramUploaderEngine


class InstagramUploaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("أداة الرفع التلقائي لإنستغرام ريلز | Instagram Auto-Uploader")
        self.root.geometry("980x750")
        self.root.minsize(850, 650)

        # محرك الرفع
        self.engine = InstagramUploaderEngine(work_dir=os.path.dirname(os.path.abspath(__file__)))
        self.worker_thread = None

        # قائمة الفيديوهات: [{"path": str, "name": str, "size": str, "status": str, "id": str}]
        self.videos_queue = []

        self._configure_styles()
        self._build_ui()
        self._check_existing_session()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # ألوان متناسقة وعصرية
        self.bg_color = "#f8f9fa"
        self.card_bg = "#ffffff"
        self.primary_color = "#E1306C"  # لون إنستغرام المميز
        self.text_color = "#212529"

        self.root.configure(bg=self.bg_color)

        style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground="#333333")
        style.configure("Card.TFrame", background=self.card_bg, relief="groove")

        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#E1306C",
            foreground="#ffffff",
            padding=6,
        )
        style.map("Primary.TButton", background=[("active", "#c1275d")])

        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            padding=5,
        )

        style.configure(
            "Stop.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#dc3545",
            foreground="#ffffff",
            padding=6,
        )
        style.map("Stop.TButton", background=[("active", "#bd2130")])

        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        # الحاوية الرئيسية مع شريط تمرير إن لزم
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---------------- 1. شريط الحساب وتسجيل الدخول ----------------
        acc_frame = ttk.LabelFrame(main_frame, text=" 👤 إعدادات حساب إنستغرام (Instagram Account) ", padding=10)
        acc_frame.pack(fill=tk.X, pady=(0, 10))

        # تبويبات طرق تسجيل الدخول
        self.login_notebook = ttk.Notebook(acc_frame)
        self.login_notebook.pack(fill=tk.X, pady=(0, 5))

        # التبويب 1: كود الجلسة (Session ID) - الأضمن والحل لمشكلة التطبيق القديم
        tab_session = ttk.Frame(self.login_notebook, padding=8)
        self.login_notebook.add(tab_session, text=" ⭐ عبر كود الجلسة (Session ID) - حل مشكلة تحديث التطبيق ")

        s_row1 = ttk.Frame(tab_session)
        s_row1.pack(fill=tk.X, pady=2)
        ttk.Label(s_row1, text="كود Session ID:").pack(side=tk.LEFT, padx=5)
        self.entry_sessionid = ttk.Entry(s_row1, width=42, font=("Segoe UI", 9))
        self.entry_sessionid.pack(side=tk.LEFT, padx=5)

        self.btn_login_session = ttk.Button(
            s_row1,
            text="🚀 تسجيل الدخول بكود الجلسة",
            style="Primary.TButton",
            command=self._start_login_session
        )
        self.btn_login_session.pack(side=tk.LEFT, padx=10)

        btn_help_session = ttk.Button(
            s_row1,
            text="❓ كيف أحصل على Session ID؟",
            style="Secondary.TButton",
            command=self._show_session_help
        )
        btn_help_session.pack(side=tk.LEFT, padx=5)

        # التبويب 2: اسم المستخدم وكلمة المرور
        tab_pass = ttk.Frame(self.login_notebook, padding=8)
        self.login_notebook.add(tab_pass, text=" 👤 اسم المستخدم وكلمة المرور (Username & Password) ")

        p_row1 = ttk.Frame(tab_pass)
        p_row1.pack(fill=tk.X, pady=2)
        ttk.Label(p_row1, text="اسم المستخدم (Username):").pack(side=tk.LEFT, padx=5)
        self.entry_user = ttk.Entry(p_row1, width=18, font=("Segoe UI", 10))
        self.entry_user.pack(side=tk.LEFT, padx=5)

        ttk.Label(p_row1, text="كلمة المرور:").pack(side=tk.LEFT, padx=(10, 5))
        self.entry_pass = ttk.Entry(p_row1, width=18, show="*", font=("Segoe UI", 10))
        self.entry_pass.pack(side=tk.LEFT, padx=5)

        self.btn_login = ttk.Button(p_row1, text="🔑 تسجيل الدخول", style="Primary.TButton", command=self._start_login)
        self.btn_login.pack(side=tk.LEFT, padx=10)

        # صف الحالة والبروكسي العام
        status_row = ttk.Frame(acc_frame)
        status_row.pack(fill=tk.X, pady=(6, 0))

        self.lbl_status = ttk.Label(status_row, text="الحالة: غير متصل ❌", foreground="#dc3545", font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=5)

        ttk.Label(status_row, text="بروكسي (اختياري):").pack(side=tk.LEFT, padx=(25, 5))
        self.entry_proxy = ttk.Entry(status_row, width=35, font=("Segoe UI", 9))
        self.entry_proxy.pack(side=tk.LEFT, padx=5)
        ttk.Label(status_row, text="(http://ip:port)", foreground="#6c757d", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)

        # ---------------- 2. اختيار الفيديوهات وقائمة الانتظار ----------------
        queue_frame = ttk.LabelFrame(main_frame, text=" 🎬 قائمة الفيديوهات للرفع (Videos Queue) ", padding=10)
        queue_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_bar = ttk.Frame(queue_frame)
        btn_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(btn_bar, text="➕ إضافة ملفات فيديو", style="Secondary.TButton", command=self._add_files).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_bar, text="📁 إضافة مجلد كامل", style="Secondary.TButton", command=self._add_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_bar, text="➖ حذف المحدد", style="Secondary.TButton", command=self._remove_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_bar, text="🗑 مسح الكل", style="Secondary.TButton", command=self._clear_queue).pack(side=tk.LEFT, padx=4)

        self.lbl_queue_count = ttk.Label(btn_bar, text="إجمالي الفيديوهات: 0", font=("Segoe UI", 9, "bold"))
        self.lbl_queue_count.pack(side=tk.RIGHT, padx=10)

        # جدول الفيديوهات
        tree_scroll = ttk.Scrollbar(queue_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            queue_frame,
            columns=("index", "name", "size", "status"),
            show="headings",
            yscrollcommand=tree_scroll.set,
            height=6
        )
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("index", text="#")
        self.tree.heading("name", text="اسم الفيديو (Video Name)")
        self.tree.heading("size", text="الحجم")
        self.tree.heading("status", text="حالة الرفع")

        self.tree.column("index", width=40, anchor=tk.CENTER)
        self.tree.column("name", width=500, anchor=tk.W)
        self.tree.column("size", width=90, anchor=tk.CENTER)
        self.tree.column("status", width=140, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # ---------------- 3. إعدادات النشر والكابشن ----------------
        settings_frame = ttk.LabelFrame(main_frame, text=" 📝 إعدادات الوصف والجدولة (Caption & Timing) ", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        s_grid = ttk.Frame(settings_frame)
        s_grid.pack(fill=tk.X)

        # الكابشن
        c_left = ttk.Frame(s_grid)
        c_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ttk.Label(c_left, text="قالب الوصف (Caption) - يمكنك استخدام {filename} لوضع اسم الفيديو:").pack(anchor=tk.W)
        self.txt_caption = tk.Text(c_left, height=3, font=("Segoe UI", 9))
        self.txt_caption.insert("1.0", "{filename}\n\nتابع للمزيد! 🚀")
        self.txt_caption.pack(fill=tk.X, pady=4)

        # الهاشتاجات والفاصل الزمني
        c_right = ttk.Frame(s_grid)
        c_right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        ttk.Label(c_right, text="الهاشتاجات (Hashtags):").pack(anchor=tk.W)
        self.entry_hashtags = ttk.Entry(c_right, width=35, font=("Segoe UI", 9))
        self.entry_hashtags.insert(0, "#shorts #reels #explore #viral #instagram")
        self.entry_hashtags.pack(fill=tk.X, pady=4)

        t_row = ttk.Frame(c_right)
        t_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(t_row, text="الفاصل بين الفيديوهات (بالدقائق):").pack(side=tk.LEFT)
        self.spin_delay = ttk.Spinbox(t_row, from_=1, to=180, width=5, font=("Segoe UI", 9))
        self.spin_delay.set(15)  # 15 دقيقة فاصل آمن جداً
        self.spin_delay.pack(side=tk.LEFT, padx=5)

        ttk.Label(c_right, text="⚠️ يُنصح بـ 15 دقيقة على الأقل لحماية الحساب من الحظر", foreground="#e65100", font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(2, 0))

        # ---------------- 4. شريط التحكم ونوافذ السجل ----------------
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 6))

        self.btn_start = ttk.Button(control_frame, text="🚀 بدء الرفع التلقائي الآن", style="Primary.TButton", command=self._start_upload_process)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(control_frame, text="⏹ إيقاف العملية", style="Stop.TButton", state=tk.DISABLED, command=self._stop_upload_process)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(control_frame, orient="horizontal", mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15)

        # نافذة السجلات (Logs)
        log_frame = ttk.LabelFrame(main_frame, text=" 📋 سجل الأحداث والمتابعة المباشرة (Activity Log) ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = ScrolledText(log_frame, height=5, font=("Consolas", 9), bg="#1e1e1e", fg="#00ff66", insertbackground="white")
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def log(self, text: str):
        def _append():
            self.txt_log.insert(tk.END, text + "\n")
            self.txt_log.see(tk.END)
        self.root.after(0, _append)

    def _check_existing_session(self):
        if self.engine.session_file.exists():
            self.lbl_status.config(text="يوجد ملف جلسة محفوظ (جاهز للفحص) ⏳", foreground="#0d6efd")
            self.log("تم العثور على جلسة سابقة (session.json). يمكنك إدخال اسم المستخدم والضغط على 'تسجيل الدخول' للتفعيل.")

    def _show_session_help(self):
        msg = (
            "📌 كيفية الحصول على Session ID في دقيقة واحدة:\n\n"
            "1. افتح متصفحك (Google Chrome أو Edge أو Brave) وسجل دخولك على instagram.com\n"
            "2. اضغط زر F12 من الكيبورد (أو اضغط كليك يمين في أي مكان ثم 'Inspect' أو 'فحص').\n"
            "3. من القائمة العلوية لأدوات المطور، اضغط على تبويب 'Application' (أو 'Storage' في فايرفوكس).\n"
            "4. من القائمة الجانبية اليسرى، افتح قسم 'Cookies' واضغط على 'https://www.instagram.com'.\n"
            "5. ستجد في الجدول عنصراً اسمه 'sessionid'؛ انسخ القيمة المقابلة له (Value).\n"
            "6. الصق القيمة في الحقل واضغط على 'تسجيل الدخول بكود الجلسة'.\n\n"
            "⭐ هذه الطريقة تتجاوز بالكامل خطأ 'Your version of Instagram is out of date' وتعتبر الأكثر أماناً."
        )
        messagebox.showinfo("دليل الحصول على Session ID", msg)

    def _start_login_session(self):
        sessionid = self.entry_sessionid.get().strip()
        proxy = self.entry_proxy.get().strip()

        if not sessionid:
            messagebox.showwarning("تنبيه", "يرجى لصق كود Session ID أولاً.\nاضغط على '❓ كيف أحصل على Session ID؟' لمعرفة الطريقة.")
            return

        self.btn_login_session.config(state=tk.DISABLED)
        self.lbl_status.config(text="جاري فحص كود الجلسة... ⏳", foreground="#ffc107")

        def task():
            success = self.engine.login_by_sessionid(
                sessionid=sessionid,
                proxy=proxy if proxy else None,
                logger_callback=self.log
            )
            def update_ui():
                self.btn_login_session.config(state=tk.NORMAL)
                if success:
                    user = getattr(self.engine.client, "username", "متصل")
                    self.lbl_status.config(text=f"متصل: @{user} ✅", foreground="#198754")
                    messagebox.showinfo("نجاح", f"تم تسجيل الدخول بنجاح بحساب @{user} وتم حفظ الجلسة!")
                else:
                    self.lbl_status.config(text="فشل تسجيل الدخول ❌", foreground="#dc3545")
                    messagebox.showerror("خطأ", "فشل التحقق من كود Session ID. تأكد من نسخه بشكل كامل وصحيح من المتصفح.")
            self.root.after(0, update_ui)

        threading.Thread(target=task, daemon=True).start()

    def _start_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        proxy = self.entry_proxy.get().strip()

        if not username:
            messagebox.showwarning("تنبيه", "يرجى كتابة اسم المستخدم (Username).")
            return

        self.btn_login.config(state=tk.DISABLED)
        self.lbl_status.config(text="جاري التحقق... ⏳", foreground="#ffc107")

        def login_task():
            def ask_2fa():
                # طلب كود 2FA عبر نافذة منبثقة في الخيط الرئيسي
                res = []
                def _popup():
                    code = simpledialog.askstring("المصادقة الثنائية (2FA)", "أدخل كود التحقق المرسل لهاتفك أو تطبيق المصادقة:")
                    res.append(code)
                self.root.after(0, _popup)
                # انتظار الإدخال
                while not res:
                    import time
                    time.sleep(0.5)
                return res[0]

            success = self.engine.login(
                username=username,
                password=password,
                proxy=proxy if proxy else None,
                two_factor_callback=ask_2fa,
                logger_callback=self.log
            )

            def update_ui():
                self.btn_login.config(state=tk.NORMAL)
                if success:
                    self.lbl_status.config(text=f"متصل: @{username} ✅", foreground="#198754")
                    messagebox.showinfo("نجاح", "تم تسجيل الدخول بنجاح! حسابك جاهز لرفع الفيديوهات.")
                else:
                    self.lbl_status.config(text="فشل تسجيل الدخول ❌", foreground="#dc3545")
                    messagebox.showerror("خطأ", "فشل تسجيل الدخول. راجع سجل الأحداث للتحقق من السبب.")

            self.root.after(0, update_ui)

        threading.Thread(target=login_task, daemon=True).start()

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="اختر فيديوهات لرفعها",
            filetypes=[("ملفات الفيديو", "*.mp4 *.mov *.avi *.m4v"), ("كل الملفات", "*.*")]
        )
        if files:
            for f in files:
                self._insert_video_to_queue(f)
            self._update_queue_label()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="اختر مجلد الفيديوهات")
        if folder:
            valid_exts = {".mp4", ".mov", ".avi", ".m4v"}
            found = 0
            for root_dir, _, filenames in os.walk(folder):
                for fname in sorted(filenames):
                    if Path(fname).suffix.lower() in valid_exts:
                        full_path = os.path.join(root_dir, fname)
                        self._insert_video_to_queue(full_path)
                        found += 1
            self._update_queue_label()
            self.log(f"تمت إضافة {found} فيديو من المجلد: {folder}")

    def _insert_video_to_queue(self, path: str):
        # منع تكرار إضافة نفس الملف في القائمة
        for item in self.videos_queue:
            if item["path"] == path:
                return

        p = Path(path)
        size_mb = f"{p.stat().st_size / (1024 * 1024):.1f} MB" if p.exists() else "0 MB"
        idx = len(self.videos_queue) + 1
        item_id = str(idx)

        # فحص إذا تم رفعه مسبقاً
        status = "في الانتظار"
        if str(p.resolve()) in self.engine.uploaded_history:
            status = "تم رفعه مسبقاً ⚠️"

        video_entry = {
            "id": item_id,
            "path": path,
            "name": p.name,
            "size": size_mb,
            "status": status
        }
        self.videos_queue.append(video_entry)
        self.tree.insert("", tk.END, iid=item_id, values=(idx, p.name, size_mb, status))

    def _remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        for item_id in selected:
            self.tree.delete(item_id)
            self.videos_queue = [v for v in self.videos_queue if v["id"] != item_id]
        self._reindex_tree()
        self._update_queue_label()

    def _clear_queue(self):
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        self.videos_queue.clear()
        self._update_queue_label()

    def _reindex_tree(self):
        for i, item in enumerate(self.videos_queue):
            idx = i + 1
            item["id"] = str(idx)
            # تحديث العرض
        # إعادة بناء الجدول
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        for i, item in enumerate(self.videos_queue):
            self.tree.insert("", tk.END, iid=item["id"], values=(i + 1, item["name"], item["size"], item["status"]))

    def _update_queue_label(self):
        self.lbl_queue_count.config(text=f"إجمالي الفيديوهات: {len(self.videos_queue)}")

    def _start_upload_process(self):
        if not self.engine.is_logged_in():
            messagebox.showwarning("تنبيه", "يرجى تسجيل الدخول إلى حساب إنستغرام أولاً.")
            return

        pending_videos = [v for v in self.videos_queue if v["status"] in ["في الانتظار", "فشل"]]
        if not pending_videos:
            messagebox.showinfo("تنبيه", "لا توجد فيديوهات بحالة 'في الانتظار' للرفع.")
            return

        try:
            delay = int(self.spin_delay.get())
        except ValueError:
            delay = 15

        caption_template = self.txt_caption.get("1.0", tk.END).strip()
        hashtags = self.entry_hashtags.get().strip()

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.progress["value"] = 0
        self.progress["maximum"] = len(pending_videos)

        def progress_tracker(current, total, v_path, status):
            def _update():
                self.progress["value"] = current
                # تحديث حالة السطر في الجدول
                for item in self.videos_queue:
                    if item["path"] == v_path:
                        arabic_status = {
                            "uploading": "جاري الرفع... ⏳",
                            "completed": "تم بنجاح ✅",
                            "failed": "فشل ❌",
                            "rate_limited": "توقف (محدود) ⛔"
                        }.get(status, status)
                        item["status"] = arabic_status
                        if self.tree.exists(item["id"]):
                            self.tree.item(item["id"], values=(item["id"], item["name"], item["size"], arabic_status))
                        break

            self.root.after(0, _update)

        def runner():
            self.engine.start_batch_upload(
                video_list=pending_videos,
                caption_template=caption_template,
                hashtags=hashtags,
                delay_minutes=delay,
                progress_callback=progress_tracker,
                logger_callback=self.log
            )
            def _finish():
                self.btn_start.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                messagebox.showinfo("اكتمال", "اكتملت عملية المعالجة لقائمة الفيديوهات!")
            self.root.after(0, _finish)

        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()

    def _stop_upload_process(self):
        if messagebox.askyesno("تأكيد", "هل أنت متأكد من رغبتك في إيقاف عملية الرفع التلقائي؟"):
            self.engine.stop()
            self.log("جاري طلب إيقاف الرفع التلقائي...")
            self.btn_stop.config(state=tk.DISABLED)


def launch():
    root = tk.Tk()
    app = InstagramUploaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
