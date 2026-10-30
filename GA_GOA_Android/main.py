# -*- coding: utf-8 -*-
"""
GA–GOA 13 tugunli elektr tarmog'i — Android/Kivy interfeysi.
Hisoblash yadrosi ga_goa_compare.py modulidan foydalanadi.
"""
import os
import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup

import ga_goa_compare as model

MODES = {
    "0 — Бошланғич режим": "0",
    "1 — Q оптималлаштириш (GA–GOA)": "1",
    "2 — Трансформатор (GA–GOA)": "2",
    "3 — Q + трансформатор (GA–GOA)": "3",
}
TITLE = {
    "0": "БОШЛАНҒИЧ РЕЖИМ — ОПТИМАЛЛАШТИРИШСИЗ",
    "1": "Q НИ GA–GOA БИЛАН ОПТИМАЛЛАШТИРИШ",
    "2": "ТРАНСФОРМАТОРНИ GA–GOA БИЛАН ОПТИМАЛЛАШТИРИШ",
    "3": "Q + ТРАНСФОРМАТОРНИ GA–GOA БИЛАН ОПТИМАЛЛАШТИРИШ",
}

def make_label(text, size=14, height=None, bold=False):
    return Label(text=text, size_hint_y=None, height=dp(height or 30),
                 font_size=sp(size), bold=bold, halign="left", valign="middle",
                 color=(0.08, 0.12, 0.18, 1), text_size=(None, None))

def sp(n):
    return dp(n)

class MainView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(7), **kwargs)
        self.add_widget(Label(text="GA–GOA: 13 ТУГУНЛИ ЭЛЕКТР ТАРМОҒИ",
                              size_hint_y=None, height=dp(44), font_size=sp(18),
                              bold=True, color=(0.05,0.2,0.38,1)))
        self.add_widget(make_label("Ҳисоблаш режимини танланг", 14))
        self.mode = Spinner(text="0 — Бошланғич режим",
                            values=list(MODES.keys()), size_hint_y=None, height=dp(44))
        self.add_widget(self.mode)

        grid = GridLayout(cols=2, spacing=dp(7), size_hint_y=None, height=dp(150))
        self.pop = TextInput(text="20", multiline=False, input_filter="int",
                             hint_text="Популяция", size_hint_y=None, height=dp(42))
        self.iters = TextInput(text="30", multiline=False, input_filter="int",
                               hint_text="Авлодлар", size_hint_y=None, height=dp(42))
        self.seed = TextInput(text="42", multiline=False, input_filter="int",
                              hint_text="Seed", size_hint_y=None, height=dp(42))
        self.vmin = TextInput(text="0.95", multiline=False, input_filter="float",
                              hint_text="V min, p.u.", size_hint_y=None, height=dp(42))
        self.vmax = TextInput(text="1.05", multiline=False, input_filter="float",
                              hint_text="V max, p.u.", size_hint_y=None, height=dp(42))
        grid.add_widget(self.pop); grid.add_widget(self.iters)
        grid.add_widget(self.seed); grid.add_widget(self.vmin)
        grid.add_widget(self.vmax); grid.add_widget(Label(text="V чегаралари (p.u.)", color=(.3,.3,.3,1)))
        self.add_widget(grid)

        self.run_btn = Button(text="ҲИСОБЛАШ", size_hint_y=None, height=dp(48),
                              background_normal="", background_color=(0.08,0.38,0.68,1))
        self.run_btn.bind(on_release=self.run_calculation)
        self.add_widget(self.run_btn)

        self.status = Label(text="DATA_Q14.txt: 13 тугун, 20 шохобча",
                            size_hint_y=None, height=dp(28), font_size=sp(12),
                            color=(0.25,0.3,0.35,1))
        self.add_widget(self.status)

        scroll = ScrollView()
        self.output = Label(text="Ҳисоблаш натижалари шу ерда чиқади.",
                            size_hint_y=None, halign="left", valign="top",
                            font_name="Roboto", font_size=sp(13),
                            color=(0.05,0.08,0.12,1), markup=False)
        self.output.bind(width=lambda inst, width: setattr(inst, "text_size", (width-dp(12), None)))
        self.output.bind(texture_size=lambda inst, size: setattr(inst, "height", size[1]+dp(20)))
        scroll.add_widget(self.output)
        self.add_widget(scroll)

    def run_calculation(self, *_):
        try:
            choice = MODES[self.mode.text]
            pop = int(self.pop.text or "20")
            iters = int(self.iters.text or "30")
            seed = int(self.seed.text or "42")
            vmin = float(self.vmin.text or ".95")
            vmax = float(self.vmax.text or "1.05")
            if choice != "0" and (pop < 4 or iters < 1):
                raise ValueError("Популяция камида 4, авлод камида 1 бўлиши керак.")
            if vmin >= vmax:
                raise ValueError("Vmin Vmax дан кичик бўлиши керак.")
        except Exception as exc:
            Popup(title="Киритиш хатоси", content=Label(text=str(exc)),
                  size_hint=(.9,.35)).open()
            return

        self.run_btn.disabled = True
        self.status.text = "Ҳисобланмоқда..."
        self.output.text = ""
        threading.Thread(target=self._worker, args=(choice,pop,iters,seed,vmin,vmax), daemon=True).start()

    def _worker(self, choice, pop, iters, seed, vmin, vmax):
        try:
            buses, branches = model.read_data(model.DATA_FILE)
            if choice == "0":
                result = model.evaluate(buses, branches, vmin=vmin, vmax=vmax)
                title = TITLE[choice]
                opt = None
            else:
                mode_map = {"1":"qgoa", "2":"tapgoa", "3":"combinedgoa"}
                opt = model.optimize(buses, branches, mode_map[choice],
                                     pop=pop, iters=iters, seed=seed, vmin=vmin, vmax=vmax)
                result = opt["e"]
                title = TITLE[choice]
            text = self.format_result(title, result, opt, choice)
            self._save_result(result, choice)
            Clock.schedule_once(lambda dt: self._finish(text, "Ҳисоблаш тугади."), 0)
        except Exception as exc:
            error_text = repr(exc)
            Clock.schedule_once(lambda dt, msg=error_text: self._finish("ХАТО: " + msg, "Хатолик"), 0)

    def format_result(self, title, res, opt, choice):
        lines = ["="*56, title, "="*56]
        if not res.get("ok"):
            return "\n".join(lines + ["ҲИСОБЛАШ ХАТОСИ: " + str(res.get("error","номаълум"))])
        lines += [f"Усул: AC Newton–Raphson",
                  f"Итерация: {res['iterations']} | max номослик: {res['mis']:.7g} МВА"]
        if opt is not None:
            lines.append(f"Мақсад функцияси: {opt['fit']:.7f}")
            if choice in ("1","3"):
                lines.append(f"Оптимал Q (9-тугун): {opt['c']['q']:.4f} МВАр")
            for t in opt["c"]["t"]:
                b = branches_for_display(t["k"])
                lines.append(f"Трансформатор {b}: Kre={t['kre']:.5f}; Kim={t['kim']:.5f}")
        lines += ["", "ТУГУНЛАР: U (кВ), δ (рад), P (МВт), Q (МВАр)",
                  f"{'№':>3} {'U,кВ':>9} {'δ,рад':>9} {'P,МВт':>10} {'Q,МВАр':>10}",
                  "-"*48]
        violated = {int(v["bus"]) for v in res.get("viol",[])}
        for r in sorted(res["rows"], key=lambda x:x["bus"]):
            mark = " !" if int(r["bus"]) in violated else ""
            lines.append(f"{r['bus']:>3} {r['u']:>9.4f} {r['d']:>9.4f} {r['p']:>10.4f} {r['q']:>10.4f}{mark}")
        lines += ["", "НИСБИЙ КУЧЛАНИШ ВА ҲИСОБЛАНГАН ИНЪЕКЦИЯЛАР",
                  f"{'№':>3} {'U,p.u.':>9} {'P ҳисоб':>11} {'Q ҳисоб':>11}",
                  "-"*39]
        for r in sorted(res["rows"], key=lambda x:x["bus"]):
            mark = " !" if int(r["bus"]) in violated else ""
            lines.append(f"{r['bus']:>3} {r['vpu']:>9.5f} {r['p_inj']:>11.4f} {r['q_inj']:>11.4f}{mark}")
        lines += ["-"*39, "", "УМУМИЙ НАТИЖАЛАР",
                  f"Актив исроф:   {res['lossP']:.4f} МВт",
                  f"Реактив исроф: {res['lossQ']:.4f} МВАр",
                  f"Чеклов бузилган тугунлар: {len(violated)}"]
        if violated:
            lines.append("Тугунлар: " + ", ".join(map(str, sorted(violated))))
        return "\n".join(lines)

    def _save_result(self, result, choice):
        if not result.get("ok"):
            return
        names={"0":"android_baseline","1":"android_q_ga_goa","2":"android_tap_ga_goa","3":"android_combined_ga_goa"}
        # The model save helper uses its configured results directory.
        model.save_csv(result, names[choice])

    def _finish(self, text, status):
        self.output.text = text
        self.run_btn.disabled = False
        self.status.text = status

def branches_for_display(index):
    # Read the same DATA_Q14.txt branch ordering as the core model.
    _, branches = model.read_data(model.DATA_FILE)
    b = branches[index]
    return f"{b.fr}-{b.to}"

class GA_GOA_AndroidApp(App):
    def build(self):
        self.title = "GA–GOA Elektr Tarmog'i"
        # Android'da natijalarni ilovaning yozish mumkin bo'lgan katalogiga saqlash.
        model.OUT_DIR = os.path.join(self.user_data_dir, "results")
        os.makedirs(model.OUT_DIR, exist_ok=True)
        return MainView()

if __name__ == "__main__":
    GA_GOA_AndroidApp().run()
