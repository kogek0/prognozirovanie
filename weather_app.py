"""
Приложение «Погода» — Open-Meteo API (без ключа, бесплатно)
Козлов К.Г., ИДБ-24-12

Запуск:
    python weather_app.py

Сборка .exe:
    pip install pyinstaller
    pyinstaller --onefile --windowed weather_app.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import urllib.request
import urllib.parse
import json
from datetime import datetime

# ─── Цвета ────────────────────────────────────────────
BG       = "#1a1a2e"
PANEL    = "#16213e"
CARD     = "#0f3460"
ACCENT   = "#e94560"
TEXT     = "#eaeaea"
SUBTEXT  = "#a0a0c0"
WHITE    = "#ffffff"
DROP_BG  = "#0d2137"
DROP_HOV = "#1a3a5c"

# ─── Иконки погоды ────────────────────────────────────
def weather_icon(code: int) -> str:
    if code == 0:              return "☀️"
    elif code in (1, 2):       return "🌤"
    elif code == 3:            return "☁️"
    elif code in (45, 48):     return "🌫"
    elif code in (51, 53, 55): return "🌦"
    elif code in (61, 63, 65): return "🌧"
    elif code in (71, 73, 75): return "❄️"
    elif code in (80, 81, 82): return "🌦"
    elif code in (95, 96, 99): return "⛈"
    else:                      return "🌡"

def weather_desc(code: int) -> str:
    descs = {
        0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность",
        3: "Пасмурно", 45: "Туман", 48: "Изморозь",
        51: "Лёгкая морось", 53: "Морось", 55: "Сильная морось",
        61: "Небольшой дождь", 63: "Дождь", 65: "Сильный дождь",
        71: "Небольшой снег", 73: "Снег", 75: "Сильный снег",
        80: "Ливень", 81: "Ливни", 82: "Сильный ливень",
        95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза",
    }
    return descs.get(code, "Неизвестно")

def wind_dir(deg: float) -> str:
    dirs = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    return dirs[round(deg / 45) % 8]

# ─── API ──────────────────────────────────────────────
def fetch_suggestions(query: str) -> list:
    """До 8 подсказок городов по введённому тексту."""
    url = (f"https://geocoding-api.open-meteo.com/v1/search"
           f"?name={urllib.parse.quote(query)}&count=8&language=ru&format=json")
    with urllib.request.urlopen(url, timeout=5) as r:
        data = json.loads(r.read())
    out = []
    for res in data.get("results", []):
        name    = res.get("name", "")
        country = res.get("country", "")
        region  = res.get("admin1", "")
        label   = name
        if region:  label += f", {region}"
        if country: label += f"  ({country})"
        out.append({"label": label, "name": name,
                    "lat": res["latitude"], "lon": res["longitude"]})
    return out

def geocode_first(city: str):
    url = (f"https://geocoding-api.open-meteo.com/v1/search"
           f"?name={urllib.parse.quote(city)}&count=1&language=ru&format=json")
    with urllib.request.urlopen(url, timeout=8) as r:
        data = json.loads(r.read())
    if not data.get("results"):
        raise ValueError(f"Город «{city}» не найден")
    res = data["results"][0]
    return res["latitude"], res["longitude"], res.get("name", city)

def fetch_weather(lat: float, lon: float) -> dict:
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
        f"wind_speed_10m,wind_direction_10m,weathercode,precipitation"
        f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"wind_speed_10m_max,sunrise,sunset"
        f"&timezone=auto&forecast_days=7"
    )
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read())


# ─── Выпадающий список подсказок ──────────────────────
class Dropdown(tk.Toplevel):
    """Всплывающий список под строкой поиска."""

    def __init__(self, parent_entry: tk.Entry, on_select):
        super().__init__(parent_entry.winfo_toplevel())
        self.overrideredirect(True)      # без рамки ОС
        self.attributes("-topmost", True)
        self.configure(bg=DROP_BG)
        self.on_select  = on_select
        self._entry     = parent_entry
        self._buttons   = []

        self._frame = tk.Frame(self, bg=DROP_BG,
                               highlightthickness=1,
                               highlightbackground="#2a4a6a")
        self._frame.pack(fill="both", expand=True)
        self.withdraw()

    def show(self, items: list):
        # Удалить старые строки
        for b in self._buttons:
            b.destroy()
        self._buttons.clear()

        if not items:
            self.withdraw()
            return

        for item in items:
            row = tk.Frame(self._frame, bg=DROP_BG, cursor="hand2")
            row.pack(fill="x")

            # Иконка города
            tk.Label(row, text="📍", font=("Segoe UI Emoji", 10),
                     bg=DROP_BG, fg=SUBTEXT, padx=6).pack(side="left")

            # Название
            lbl = tk.Label(row, text=item["label"],
                           font=("Segoe UI", 10), bg=DROP_BG, fg=TEXT,
                           anchor="w", padx=4, pady=7)
            lbl.pack(side="left", fill="x", expand=True)

            # Разделитель
            sep = tk.Frame(self._frame, bg="#1a3a5c", height=1)
            sep.pack(fill="x")

            # Hover + клик на всей строке
            for widget in (row, lbl):
                widget.bind("<Enter>", lambda e, r=row, l=lbl, s=sep:
                            (r.config(bg=DROP_HOV), l.config(bg=DROP_HOV),
                             s.config(bg=DROP_HOV)))
                widget.bind("<Leave>", lambda e, r=row, l=lbl, s=sep:
                            (r.config(bg=DROP_BG), l.config(bg=DROP_BG),
                             s.config(bg="#1a3a5c")))
                widget.bind("<Button-1>", lambda e, it=item: self._pick(it))

            self._buttons.append(row)

        self._reposition(len(items))
        self.deiconify()

    def _reposition(self, count: int):
        self._entry.update_idletasks()
        x  = self._entry.winfo_rootx()
        y  = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        w  = self._entry.winfo_width()
        h  = min(count, 8) * 38
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _pick(self, item: dict):
        self.withdraw()
        self.on_select(item)

    def hide(self):
        self.withdraw()


# ─── Главное окно ─────────────────────────────────────
class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Погода")
        self.geometry("820x640")
        self.minsize(700, 540)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._suggest_timer = None

        self._build_ui()
        self.bind("<Button-1>", self._on_root_click)

    def _build_ui(self):
        # ── Строка поиска ──
        search_frame = tk.Frame(self, bg=BG)
        search_frame.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(search_frame, text="🌍", font=("Segoe UI Emoji", 18),
                 bg=BG, fg=TEXT).pack(side="left", padx=(0, 8))

        self.city_var = tk.StringVar()
        self.entry = tk.Entry(
            search_frame, textvariable=self.city_var,
            font=("Segoe UI", 14), bg=PANEL, fg=WHITE,
            insertbackground=WHITE, relief="flat",
            bd=0, highlightthickness=2,
            highlightbackground=CARD, highlightcolor=ACCENT)
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        self.entry.bind("<Return>",     lambda e: self._search_by_text())
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Escape>",     lambda e: self.dropdown.hide())

        self.search_btn = tk.Button(
            search_frame, text="Найти",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg=WHITE, activebackground="#c73652",
            relief="flat", bd=0, padx=20, pady=8,
            cursor="hand2", command=self._search_by_text)
        self.search_btn.pack(side="left")

        # ── Статус ──
        self.status_var = tk.StringVar(value="Введите город — подсказки появятся автоматически")
        tk.Label(self, textvariable=self.status_var,
                 font=("Segoe UI", 9), bg=BG, fg=SUBTEXT).pack(pady=(6, 0))

        # ── Прогресс ──
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=300)

        # ── Контент ──
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True, padx=24, pady=12)

        # ── Дропдаун (создаём после entry) ──
        self.dropdown = Dropdown(self.entry, self._on_suggestion_pick)

    # ── АВТОДОПОЛНЕНИЕ ────────────────────────────────
    def _on_key(self, event=None):
        if event and event.keysym in ("Return", "Escape", "Up", "Down",
                                      "Left", "Right", "Tab"):
            return
        query = self.city_var.get().strip()
        if len(query) < 2:
            self.dropdown.hide()
            return
        # Debounce 350 мс
        if self._suggest_timer:
            self.after_cancel(self._suggest_timer)
        self._suggest_timer = self.after(350, lambda: self._load_suggestions(query))

    def _load_suggestions(self, query: str):
        def task():
            try:
                items = fetch_suggestions(query)
                if self.city_var.get().strip() == query:
                    self.after(0, lambda: self.dropdown.show(items))
            except Exception:
                pass
        threading.Thread(target=task, daemon=True).start()

    def _on_suggestion_pick(self, item: dict):
        """Пользователь выбрал город из списка — грузим сразу по координатам."""
        self.city_var.set(item["name"])
        self.entry.icursor(tk.END)
        self._load_weather_direct(item["lat"], item["lon"], item["label"])

    def _on_root_click(self, event):
        if event.widget is not self.entry:
            self.dropdown.hide()

    # ── ПОИСК ────────────────────────────────────────
    def _search_by_text(self):
        city = self.city_var.get().strip()
        if not city:
            return
        self.dropdown.hide()
        self._start_loading()
        threading.Thread(target=self._load_by_name, args=(city,), daemon=True).start()

    def _load_by_name(self, city: str):
        try:
            lat, lon, name = geocode_first(city)
            data = fetch_weather(lat, lon)
            self.after(0, lambda: self._show(data, name, lat, lon))
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _load_weather_direct(self, lat: float, lon: float, label: str):
        self._start_loading()
        def task():
            try:
                data = fetch_weather(lat, lon)
                self.after(0, lambda: self._show(data, label, lat, lon))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))
        threading.Thread(target=task, daemon=True).start()

    def _start_loading(self):
        self.search_btn.config(state="disabled")
        self.status_var.set("Загрузка…")
        self.progress.pack(pady=4)
        self.progress.start(10)

    def _on_error(self, msg: str):
        self._stop_progress()
        self.status_var.set("Ошибка")
        messagebox.showerror("Ошибка", msg)

    def _stop_progress(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.search_btn.config(state="normal")

    # ── ОТРИСОВКА ────────────────────────────────────
    def _show(self, data: dict, city_name: str, lat: float, lon: float):
        self._stop_progress()
        self.status_var.set(
            f"📍 {city_name}  •  {lat:.2f}°N  {lon:.2f}°E  "
            f"•  обновлено {datetime.now().strftime('%H:%M')}"
        )

        for w in self.content.winfo_children():
            w.destroy()

        cur   = data["current"]
        daily = data["daily"]

        # Текущая погода
        top = tk.Frame(self.content, bg=CARD)
        top.pack(fill="x", pady=(0, 12))
        top.columnconfigure(1, weight=1)

        tk.Label(top, text=weather_icon(cur["weathercode"]),
                 font=("Segoe UI Emoji", 52),
                 bg=CARD, fg=WHITE).grid(row=0, column=0, rowspan=3,
                                          padx=(20, 10), pady=16)

        tk.Label(top, text=f"{cur['temperature_2m']:+.1f}°C",
                 font=("Segoe UI", 40, "bold"),
                 bg=CARD, fg=WHITE).grid(row=0, column=1, sticky="w",
                                          padx=4, pady=(16, 0))

        tk.Label(top,
                 text=(f"Ощущается как {cur['apparent_temperature']:+.1f}°C  "
                       f"•  {weather_desc(cur['weathercode'])}"),
                 font=("Segoe UI", 11), bg=CARD, fg=SUBTEXT).grid(
                     row=1, column=1, sticky="w", padx=4)

        tk.Label(top,
                 text=(f"💧 Влажность: {cur['relative_humidity_2m']}%    "
                       f"💨 Ветер: {cur['wind_speed_10m']} км/ч "
                       f"{wind_dir(cur['wind_direction_10m'])}    "
                       f"🌧 Осадки: {cur['precipitation']} мм"),
                 font=("Segoe UI", 10), bg=CARD, fg=TEXT).grid(
                     row=2, column=1, sticky="w", padx=4, pady=(2, 16))

        tk.Label(top,
                 text=f"🌅 {daily['sunrise'][0][11:16]}   🌇 {daily['sunset'][0][11:16]}",
                 font=("Segoe UI", 10), bg=CARD, fg=SUBTEXT).grid(
                     row=0, column=2, rowspan=3, padx=20, pady=16, sticky="e")

        # Прогноз 7 дней
        tk.Label(self.content, text="Прогноз на 7 дней",
                 font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(4, 6))

        days_frame = tk.Frame(self.content, bg=BG)
        days_frame.pack(fill="x")
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        for i in range(7):
            dt       = datetime.strptime(daily["time"][i], "%Y-%m-%d")
            is_today = (i == 0)
            lbl_txt  = "Сегодня" if is_today else f"{day_names[dt.weekday()]}\n{dt.strftime('%d.%m')}"
            card_bg  = ACCENT if is_today else PANEL
            sub_fg   = "#ffcccc" if is_today else SUBTEXT

            card = tk.Frame(days_frame, bg=card_bg)
            card.pack(side="left", fill="both", expand=True, padx=3, pady=2)

            tk.Label(card, text=lbl_txt, font=("Segoe UI", 8, "bold"),
                     bg=card_bg, fg=WHITE, justify="center").pack(pady=(10, 2))
            tk.Label(card, text=weather_icon(daily["weathercode"][i]),
                     font=("Segoe UI Emoji", 20),
                     bg=card_bg, fg=WHITE).pack()
            tk.Label(card, text=f"{daily['temperature_2m_max'][i]:+.0f}°",
                     font=("Segoe UI", 13, "bold"),
                     bg=card_bg, fg=WHITE).pack()
            tk.Label(card, text=f"{daily['temperature_2m_min'][i]:+.0f}°",
                     font=("Segoe UI", 10), bg=card_bg, fg=sub_fg).pack()
            tk.Label(card, text=f"💧{daily['precipitation_sum'][i]:.1f}мм",
                     font=("Segoe UI", 8), bg=card_bg, fg=sub_fg).pack()
            tk.Label(card, text=f"💨{daily['wind_speed_10m_max'][i]:.0f}км/ч",
                     font=("Segoe UI", 8), bg=card_bg,
                     fg=sub_fg).pack(pady=(0, 10))

        tk.Label(self.content, text="Данные: Open-Meteo.com (CC BY 4.0)",
                 font=("Segoe UI", 8), bg=BG, fg=SUBTEXT).pack(
                     anchor="e", pady=(8, 0))


# ─── Запуск ───────────────────────────────────────────
if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()