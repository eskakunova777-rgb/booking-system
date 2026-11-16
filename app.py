"""Графический интерфейс мини-системы бронирования (tkinter).

Три вкладки: Бронирования, Пользователи, Столы. На вкладке бронирований
есть кнопка «Проверить доступность»: она вызывает
backend.check_table_availability и пишет, свободен ли стол.

Запуск: python app.py
"""

import tkinter as tk
from tkinter import messagebox, ttk

import backend
from backend import BookingError

GREEN = "#1b7f3b"
RED = "#b3261e"


class CrudTab(ttk.Frame):
    """Вкладка со списком и формой: добавить / изменить / удалить."""

    def __init__(self, master, app, columns, fields, load, create, update, delete, title):
        super().__init__(master, padding=10)
        self.app = app
        self.columns = columns          # [(ключ, заголовок, ширина)]
        self.fields = fields            # [(ключ, подпись)]
        self.load, self.create, self.update, self.delete = load, create, update, delete
        self.title = title
        self.selected_id = None

        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], show="headings", height=10)
        for key, head, width in columns:
            self.tree.heading(key, text=head)
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(self, text=title, padding=8)
        form.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        self.vars = {}
        for i, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            ttk.Entry(form, textvariable=var, width=40).grid(row=i, column=1, sticky="w", pady=2)
            self.vars[key] = var

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, columnspan=4, sticky="w", pady=8)
        ttk.Button(buttons, text="Добавить", command=self.on_create).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Сохранить изменения", command=self.on_update).pack(side="left", padx=6)
        ttk.Button(buttons, text="Удалить", command=self.on_delete).pack(side="left", padx=6)
        ttk.Button(buttons, text="Очистить форму", command=self.clear).pack(side="left", padx=6)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.refresh()

    def values(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.load():
            self.tree.insert("", "end", iid=row["id"],
                             values=[row.get(k) if row.get(k) is not None else "" for k, _, _ in self.columns])

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        row = dict(zip([c[0] for c in self.columns], self.tree.item(sel[0], "values")))
        for key in self.vars:
            self.vars[key].set(row.get(key, ""))

    def clear(self):
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())
        for var in self.vars.values():
            var.set("")

    def _do(self, action, ok_text):
        try:
            action()
        except (BookingError, ValueError) as e:
            messagebox.showerror(self.title, str(e))
            return
        self.refresh()
        self.app.refresh_all()
        self.app.status(ok_text, GREEN)

    def on_create(self):
        self._do(lambda: self.create(**self.values()), "Запись добавлена.")
        self.clear()

    def on_update(self):
        if self.selected_id is None:
            messagebox.showinfo(self.title, "Сначала выберите строку в списке.")
            return
        self._do(lambda: self.update(self.selected_id, **self.values()), "Изменения сохранены.")

    def on_delete(self):
        if self.selected_id is None:
            messagebox.showinfo(self.title, "Сначала выберите строку в списке.")
            return
        if not messagebox.askyesno(self.title, "Удалить выбранную запись? Её бронирования тоже удалятся."):
            return
        self._do(lambda: self.delete(self.selected_id), "Запись удалена.")
        self.clear()


class BookingsTab(ttk.Frame):
    COLUMNS = [("id", "№ брони", 70), ("table_number", "Стол", 60), ("user_name", "Гость", 170),
               ("date", "Дата", 100), ("time", "Время", 110), ("guests", "Гостей", 70)]

    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app
        self.selected_id = None

        self.tree = ttk.Treeview(self, columns=[c[0] for c in self.COLUMNS], show="headings", height=10)
        for key, head, width in self.COLUMNS:
            self.tree.heading(key, text=head)
            self.tree.column(key, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(self, text="Бронирование", padding=8)
        form.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.user_var, self.table_var = tk.StringVar(), tk.StringVar()
        self.date_var = tk.StringVar(value="2026-11-20")
        self.start_var, self.end_var = tk.StringVar(value="20:00"), tk.StringVar(value="22:00")
        self.guests_var = tk.StringVar(value="2")

        ttk.Label(form, text="Гость").grid(row=0, column=0, sticky="w", pady=2)
        self.user_box = ttk.Combobox(form, textvariable=self.user_var, state="readonly", width=38)
        self.user_box.grid(row=0, column=1, columnspan=3, sticky="w", pady=2)
        ttk.Label(form, text="Стол").grid(row=1, column=0, sticky="w", pady=2)
        self.table_box = ttk.Combobox(form, textvariable=self.table_var, state="readonly", width=38)
        self.table_box.grid(row=1, column=1, columnspan=3, sticky="w", pady=2)
        ttk.Label(form, text="Дата (ГГГГ-ММ-ДД)").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.date_var, width=12).grid(row=2, column=1, sticky="w", pady=2)
        ttk.Label(form, text="Время с / до (ЧЧ:ММ)").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.start_var, width=7).grid(row=3, column=1, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.end_var, width=7).grid(row=3, column=2, sticky="w", pady=2)
        ttk.Label(form, text="Гостей").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Spinbox(form, from_=1, to=20, textvariable=self.guests_var, width=5).grid(row=4, column=1, sticky="w", pady=2)

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, sticky="w", pady=8)
        ttk.Button(buttons, text="Проверить доступность", command=self.on_check).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Забронировать", command=self.on_create).pack(side="left", padx=6)
        ttk.Button(buttons, text="Сохранить изменения", command=self.on_update).pack(side="left", padx=6)
        ttk.Button(buttons, text="Удалить бронь", command=self.on_delete).pack(side="left", padx=6)

        self.result = tk.Label(self, text="", font=("Helvetica", 14, "bold"), anchor="w", justify="left")
        self.result.grid(row=3, column=0, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.refresh()

    # --- данные для выпадающих списков ---
    def refresh(self):
        self.users = {f"{u['name']} ({u['phone']})": u["id"] for u in backend.get_all_users()}
        self.tables = {f"№{t['number']}: {t['seats']} мест, {t['location'] or 'без места'}": t["id"]
                       for t in backend.get_all_tables()}
        self.user_box["values"] = list(self.users)
        self.table_box["values"] = list(self.tables)
        if self.user_var.get() not in self.users:
            self.user_var.set(next(iter(self.users), ""))
        if self.table_var.get() not in self.tables:
            self.table_var.set(next(iter(self.tables), ""))

        self.tree.delete(*self.tree.get_children())
        for b in backend.get_all_bookings():
            self.tree.insert("", "end", iid=b["id"], values=[
                b["id"], b["table_number"], b["user_name"], f"{b['start_time']:%Y-%m-%d}",
                f"{b['start_time']:%H:%M}-{b['end_time']:%H:%M}", b["guests"]])

    def form(self):
        if not self.user_var.get() or not self.table_var.get():
            raise BookingError("Выберите гостя и стол.")
        date = self.date_var.get().strip()
        return {
            "user_id": self.users[self.user_var.get()],
            "table_id": self.tables[self.table_var.get()],
            "start_time": f"{date} {self.start_var.get().strip()}",
            "end_time": f"{date} {self.end_var.get().strip()}",
            "guests": int(self.guests_var.get()),
        }

    def show(self, text, color):
        self.result.config(text=text, fg=color)

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        b = backend.get_booking(self.selected_id)
        for label, uid in self.users.items():
            if uid == b["user_id"]:
                self.user_var.set(label)
        for label, tid in self.tables.items():
            if tid == b["table_id"]:
                self.table_var.set(label)
        self.date_var.set(f"{b['start_time']:%Y-%m-%d}")
        self.start_var.set(f"{b['start_time']:%H:%M}")
        self.end_var.set(f"{b['end_time']:%H:%M}")
        self.guests_var.set(str(b["guests"]))

    def on_check(self):
        try:
            f = self.form()
            free, conflicts = backend.check_table_availability(
                f["table_id"], f["start_time"], f["end_time"])
        except (BookingError, ValueError) as e:
            self.show(f"Ошибка: {e}", RED)
            return
        when = f"{f['start_time']}-{f['end_time'][-5:]}"
        if free:
            self.show(f"✔ Стол свободен на {when}", GREEN)
        else:
            lines = [f"✘ Стол занят на {when}. Мешает:"]
            lines += [f"   бронь #{c['id']}, {c['user_name']}, "
                      f"{c['start_time']:%H:%M}-{c['end_time']:%H:%M}" for c in conflicts]
            self.show("\n".join(lines), RED)

    def _do(self, action, ok_text):
        try:
            action()
        except (BookingError, ValueError) as e:
            self.show(f"✘ {e}", RED)
            return
        self.app.refresh_all()
        self.show(ok_text, GREEN)

    def on_create(self):
        self._do(lambda: backend.create_booking(**self.form()), "✔ Бронь создана.")

    def on_update(self):
        if self.selected_id is None:
            self.show("Сначала выберите бронь в списке.", RED)
            return
        self._do(lambda: backend.update_booking(self.selected_id, **self.form()), "✔ Бронь изменена.")

    def on_delete(self):
        if self.selected_id is None:
            self.show("Сначала выберите бронь в списке.", RED)
            return
        if not messagebox.askyesno("Бронирование", f"Удалить бронь #{self.selected_id}?"):
            return
        self._do(lambda: backend.delete_booking(self.selected_id), "✔ Бронь удалена.")
        self.selected_id = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Мини-система бронирования")
        self.geometry("760x620")
        created = backend.init_db()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.bookings = BookingsTab(notebook, self)
        self.users = CrudTab(
            notebook, self,
            columns=[("id", "id", 50), ("name", "Имя", 200), ("phone", "Телефон", 160), ("email", "Почта", 200)],
            fields=[("name", "Имя"), ("phone", "Телефон"), ("email", "Почта (необязательно)")],
            load=backend.get_all_users, create=backend.create_user,
            update=backend.update_user, delete=backend.delete_user, title="Пользователь")
        self.tables = CrudTab(
            notebook, self,
            columns=[("id", "id", 50), ("number", "Номер", 80), ("seats", "Мест", 80), ("location", "Где стоит", 250)],
            fields=[("number", "Номер стола"), ("seats", "Мест"), ("location", "Где стоит")],
            load=backend.get_all_tables, create=backend.create_table,
            update=backend.update_table, delete=backend.delete_table, title="Стол")
        notebook.add(self.bookings, text="Бронирования")
        notebook.add(self.users, text="Пользователи")
        notebook.add(self.tables, text="Столы")

        self.status_bar = tk.Label(self, anchor="w", padx=10)
        self.status_bar.pack(fill="x")
        self.status("Подключено к базе. " + (f"Созданы таблицы: {', '.join(created)}." if created else "Таблицы на месте."), GREEN)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def status(self, text, color):
        self.status_bar.config(text=text, fg=color)

    def refresh_all(self):
        self.bookings.refresh()
        self.users.refresh()
        self.tables.refresh()

    def on_close(self):
        backend.close()
        self.destroy()


def main():
    try:
        app = App()
    except Exception as e:  # нет связи с базой, неверный пароль в .env и т.п.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Нет подключения к базе", f"{e}\n\nПроверьте файл .env и что PostgreSQL запущен.")
        root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
