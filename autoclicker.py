import sys
import os
import time
import json
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QDoubleSpinBox, QSpinBox, QLabel, QFileDialog, QMessageBox,
    QComboBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import pyautogui
from pynput import keyboard, mouse

pyautogui.FAILSAFE = False

ENV_SESSION = os.environ.get("XDG_SESSION_TYPE", "unknown").lower()

LANG_DATA = {
    "Русский": {
        "title": f"AutoClicker на линукс ({ENV_SESSION.upper()})",
        "sec_main": "Настройки",
        "lang": "Язык:",
        "hotkey": "Клавиша старт/стоп:",
        "hk_btn": "Назначить (сейчас: {})",
        "hk_press": "Жду нажатия...",
        "sec_points": "Список действий",
        "add_pt": "+ Точка (3с задержка)",
        "add_img": "+ Картинка",
        "rec_start": "Запись макроса",
        "rec_stop": "Остановить запись",
        "del_row": "Удалить",
        "clear": "Очистить",
        "save": "Сохранить",
        "load": "Загрузить",
        "start": "СТАРТ",
        "stop": "СТОП",
        "empty_err": "Добавьте хотя бы одно действие!",
        "err": "Ошибка",
        "cap_wait": "Захват через {}с...",
        "st_run": "Статус: Работает",
        "st_stop": "Статус: Остановлен",
        "st_rec": "Статус: Идет запись...",
        "sec_rnd": "Античит (Рандомизация)",
        "rnd_xy": "Разброс XY (px):",
        "rnd_t": "Разброс времени (сек):",
        "sec_limits": "Условие остановки",
        "limits": ["Бесконечно", "Циклы", "Таймер (сек)"]
    },
    "English": {
        "title": f"AutoClicker на линукс ({ENV_SESSION.upper()})",
        "sec_main": "Settings",
        "lang": "Language:",
        "hotkey": "Start/Stop Key:",
        "hk_btn": "Set key (Current: {})",
        "hk_press": "Press any key...",
        "sec_points": "Actions List",
        "add_pt": "+ Point (3s delay)",
        "add_img": "+ Image",
        "rec_start": "Record Macro",
        "rec_stop": "Stop Recording",
        "del_row": "Delete",
        "clear": "Clear",
        "save": "Save Profile",
        "load": "Load Profile",
        "start": "START",
        "stop": "STOP",
        "empty_err": "Action list is empty!",
        "err": "Error",
        "cap_wait": "Capturing in {}s...",
        "st_run": "Status: Running",
        "st_stop": "Status: Stopped",
        "st_rec": "Status: Recording...",
        "sec_rnd": "Anti-Cheat (Randomization)",
        "rnd_xy": "XY Spread (px):",
        "rnd_t": "Time Spread (sec):",
        "sec_limits": "Stop Condition",
        "limits": ["Infinite", "Cycles", "Timer (sec)"]
    }
}

APP_THEME = """
QWidget { background-color: #1e1e2e; color: #cdd6f4; font-size: 12px; }
QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 10px; font-weight: bold; color: #89b4fa; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 5px 8px; }
QPushButton:hover { background-color: #45475a; }
QTableWidget, QComboBox, QDoubleSpinBox, QSpinBox { background-color: #181825; border: 1px solid #45475a; border-radius: 4px; color: #cdd6f4; }
QHeaderView::section { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; }
"""

class KeyHook(QThread):
    key_pressed = pyqtSignal()

    def __init__(self, target_key):
        super().__init__()
        self.target_key = target_key
        self._listener = None

    def run(self):
        def check_key(k):
            try:
                if hasattr(k, 'name') and k.name == self.target_key:
                    self.key_pressed.emit()
                elif hasattr(k, 'char') and k.char == self.target_key:
                    self.key_pressed.emit()
            except Exception:
                pass

        with keyboard.Listener(on_press=check_key) as lst:
            self._listener = lst
            lst.join()

    def stop(self):
        if self._listener:
            self._listener.stop()


class InputRecorder(QThread):
    event_captured = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._m_listener = None
        self.last_ts = time.time()

    def run(self):
        self.last_ts = time.time()
        def on_click(x, y, btn, pressed):
            if pressed:
                now = time.time()
                dt = round(now - self.last_ts, 2)
                self.last_ts = now
                self.event_captured.emit({
                    "type": "click",
                    "x": x,
                    "y": y,
                    "delay": max(dt, 0.2),
                    "button": btn.name,
                    "click_type": "single",
                    "image": ""
                })

        with mouse.Listener(on_click=on_click) as lst:
            self._m_listener = lst
            lst.join()

    def stop(self):
        if self._m_listener:
            self._m_listener.stop()


class ClickWorker(QThread):
    finished = pyqtSignal()

    def __init__(self, items, opts):
        super().__init__()
        self.items = items
        self.opts = opts
        self.active = False

    def run(self):
        self.active = True
        t_start = time.time()
        loops = 0

        while self.active:
            if self.opts["mode"] == 1 and loops >= self.opts["max_val"]:
                break
            if self.opts["mode"] == 2 and (time.time() - t_start) >= self.opts["max_val"]:
                break

            for item in self.items:
                if not self.active:
                    break

                t_base = item["delay"]
                t_spread = self.opts["rnd_t"]
                t_actual = max(0.05, t_base + random.uniform(-t_spread, t_spread))
                time.sleep(t_actual)

                if item.get("type") == "image":
                    try:
                        pos = pyautogui.locateOnScreen(item["image"], confidence=0.8)
                        if pos:
                            cx, cy = pyautogui.center(pos)
                            self._do_click(cx, cy, item["button"], item["click_type"])
                    except Exception:
                        pass
                    continue

                p_spread = self.opts["rnd_xy"]
                final_x = item["x"] + random.randint(-p_spread, p_spread)
                final_y = item["y"] + random.randint(-p_spread, p_spread)

                self._do_click(final_x, final_y, item["button"], item["click_type"])

            loops += 1

        self.active = False
        self.finished.emit()

    def _do_click(self, x, y, btn, ctype):
        cnt = 2 if ctype == "double" else 1
        if ctype == "hold":
            pyautogui.mouseDown(x, y, button=btn)
            time.sleep(0.3)
            pyautogui.mouseUp(x, y, button=btn)
        else:
            pyautogui.click(x, y, button=btn, clicks=cnt)

    def stop(self):
        self.active = False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.lang = "Русский"
        self.current_hk = "f8"
        self.wait_hk = False

        self.click_thread = None
        self.hk_thread = None
        self.rec_thread = None

        self.build_gui()
        self.init_hook()

    def build_gui(self):
        self.setStyleSheet(APP_THEME)
        self.resize(700, 680)

        layout = QVBoxLayout(self)

        # Секция настроек
        self.grp_settings = QGroupBox()
        l_set = QHBoxLayout()
        self.lbl_l = QLabel()
        self.cbo_l = QComboBox()
        self.cbo_l.addItems(list(LANG_DATA.keys()))
        self.cbo_l.currentTextChanged.connect(self.on_lang_change)
        l_set.addWidget(self.lbl_l)
        l_set.addWidget(self.cbo_l)

        self.lbl_hk = QLabel()
        self.btn_hk = QPushButton()
        self.btn_hk.clicked.connect(self.bind_key)
        l_set.addWidget(self.lbl_hk)
        l_set.addWidget(self.btn_hk)
        self.grp_settings.setLayout(l_set)
        layout.addWidget(self.grp_settings)

        # Античит и Ограничения
        l_mid = QHBoxLayout()

        self.grp_rnd = QGroupBox()
        l_rnd = QHBoxLayout()
        self.lbl_r_xy = QLabel()
        self.spn_r_xy = QSpinBox()
        self.spn_r_xy.setRange(0, 50)
        self.spn_r_xy.setValue(5)
        
        self.lbl_r_t = QLabel()
        self.spn_r_t = QDoubleSpinBox()
        self.spn_r_t.setRange(0.0, 5.0)
        self.spn_r_t.setValue(0.35)
        self.spn_r_t.setSingleStep(0.05)

        l_rnd.addWidget(self.lbl_r_xy)
        l_rnd.addWidget(self.spn_r_xy)
        l_rnd.addWidget(self.lbl_r_t)
        l_rnd.addWidget(self.spn_r_t)
        self.grp_rnd.setLayout(l_rnd)
        l_mid.addWidget(self.grp_rnd)

        self.grp_lim = QGroupBox()
        l_lim = QHBoxLayout()
        self.cbo_lim = QComboBox()
        self.spn_lim_v = QSpinBox()
        self.spn_lim_v.setRange(1, 999999)
        self.spn_lim_v.setValue(100)
        l_lim.addWidget(self.cbo_lim)
        l_lim.addWidget(self.spn_lim_v)
        self.grp_lim.setLayout(l_lim)
        l_mid.addWidget(self.grp_lim)

        layout.addLayout(l_mid)

        # Таблица точек
        self.grp_points = QGroupBox()
        l_pts = QVBoxLayout()
        
        self.grid = QTableWidget(0, 5)
        self.grid.setHorizontalHeaderLabels(["X / Path", "Y", "Delay (s)", "Button", "Type"])
        self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l_pts.addWidget(self.grid)

        l_btns = QHBoxLayout()
        self.b_add = QPushButton()
        self.b_add.clicked.connect(self.add_single_point)
        self.b_add_img = QPushButton()
        self.b_add_img.clicked.connect(self.add_image_point)
        self.b_rec = QPushButton()
        self.b_rec.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold;")
        self.b_rec.clicked.connect(self.toggle_rec)
        self.b_del = QPushButton()
        self.b_del.clicked.connect(self.delete_row)
        self.b_clr = QPushButton()
        self.b_clr.clicked.connect(self.clear_grid)

        l_btns.addWidget(self.b_add)
        l_btns.addWidget(self.b_add_img)
        l_btns.addWidget(self.b_rec)
        l_btns.addWidget(self.b_del)
        l_btns.addWidget(self.b_clr)
        l_pts.addLayout(l_btns)
        
        self.grp_points.setLayout(l_pts)
        layout.addWidget(self.grp_points)

        # Работа с конфигами
        l_files = QHBoxLayout()
        self.b_save = QPushButton()
        self.b_save.clicked.connect(self.save_json)
        self.b_load = QPushButton()
        self.b_load.clicked.connect(self.load_json)
        l_files.addWidget(self.b_save)
        l_files.addWidget(self.b_load)
        layout.addLayout(l_files)

        # Главные кнопки управления
        self.lbl_st = QLabel()
        self.lbl_st.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_st.setStyleSheet("font-weight: bold; font-size: 13px; color: #a6adc8;")
        layout.addWidget(self.lbl_st)

        l_ctrl = QHBoxLayout()
        self.b_start = QPushButton()
        self.b_start.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; font-size: 13px;")
        self.b_start.clicked.connect(self.start)
        
        self.b_stop = QPushButton()
        self.b_stop.setEnabled(False)
        self.b_stop.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; font-size: 13px;")
        self.b_stop.clicked.connect(self.stop)

        l_ctrl.addWidget(self.b_start)
        l_ctrl.addWidget(self.b_stop)
        layout.addLayout(l_ctrl)

        self.apply_lang()

    def apply_lang(self):
        d = LANG_DATA.get(self.lang, LANG_DATA["English"])
        self.setWindowTitle(d["title"])
        self.grp_settings.setTitle(d["sec_main"])
        self.lbl_l.setText(d["lang"])
        self.lbl_hk.setText(d["hotkey"])
        if not self.wait_hk:
            self.btn_hk.setText(d["hk_btn"].format(self.current_hk.upper()))
        
        self.grp_rnd.setTitle(d["sec_rnd"])
        self.lbl_r_xy.setText(d["rnd_xy"])
        self.lbl_r_t.setText(d["rnd_t"])
        self.grp_lim.setTitle(d["sec_limits"])

        idx = max(0, self.cbo_lim.currentIndex())
        self.cbo_lim.clear()
        self.cbo_lim.addItems(d["limits"])
        self.cbo_lim.setCurrentIndex(idx)

        self.grp_points.setTitle(d["sec_points"])
        self.b_add.setText(d["add_pt"])
        self.b_add_img.setText(d["add_img"])
        
        if not (self.rec_thread and self.rec_thread.isRunning()):
            self.b_rec.setText(d["rec_start"])
        else:
            self.b_rec.setText(d["rec_stop"])

        self.b_del.setText(d["del_row"])
        self.b_clr.setText(d["clear"])
        self.b_save.setText(d["save"])
        self.b_load.setText(d["load"])
        self.b_start.setText(d["start"])
        self.b_stop.setText(d["stop"])

        if self.click_thread and self.click_thread.isRunning():
            self.lbl_st.setText(d["st_run"])
            self.lbl_st.setStyleSheet("font-weight: bold; font-size: 13px; color: #a6e3a1;")
        elif self.rec_thread and self.rec_thread.isRunning():
            self.lbl_st.setText(d["st_rec"])
            self.lbl_st.setStyleSheet("font-weight: bold; font-size: 13px; color: #f38ba8;")
        else:
            self.lbl_st.setText(d["st_stop"])
            self.lbl_st.setStyleSheet("font-weight: bold; font-size: 13px; color: #f38ba8;")

    def on_lang_change(self, new_lang):
        self.lang = new_lang
        self.apply_lang()

    def bind_key(self):
        d = LANG_DATA.get(self.lang, LANG_DATA["English"])
        self.wait_hk = True
        self.btn_hk.setText(d["hk_press"])
        self.btn_hk.setEnabled(False)

    def keyPressEvent(self, event):
        if self.wait_hk:
            k_code = event.key()
            txt = event.text().lower()

            if Qt.Key.Key_F1 <= k_code <= Qt.Key.Key_F12:
                txt = f"f{k_code - Qt.Key.Key_F1 + 1}"

            if txt:
                self.current_hk = txt
                self.wait_hk = False
                self.btn_hk.setEnabled(True)
                self.apply_lang()
                self.init_hook()
        else:
            super().keyPressEvent(event)

    def init_hook(self):
        if self.hk_thread and self.hk_thread.isRunning():
            self.hk_thread.stop()
            self.hk_thread.wait()

        self.hk_thread = KeyHook(self.current_hk)
        self.hk_thread.key_pressed.connect(self.toggle_state)
        self.hk_thread.start()

    def toggle_state(self):
        if self.click_thread and self.click_thread.isRunning():
            self.stop()
        else:
            self.start()

    def add_single_point(self):
        d = LANG_DATA.get(self.lang, LANG_DATA["English"])
        for i in range(3, 0, -1):
            self.b_add.setText(d["cap_wait"].format(i))
            QApplication.processEvents()
            time.sleep(1)

        cx, cy = pyautogui.position()
        self.push_row({
            "type": "click", "x": cx, "y": cy, "delay": 0.5, "button": "left", "click_type": "single", "image": ""
        })
        self.b_add.setText(d["add_pt"])

    def add_image_point(self):
        path, _ = QFileDialog.getOpenFileName(self, "Изображение", "", "Images (*.png *.jpg)")
        if path:
            self.push_row({
                "type": "image", "x": 0, "y": 0, "delay": 0.5, "button": "left", "click_type": "single", "image": path
            })

    def push_row(self, data):
        r = self.grid.rowCount()
        self.grid.insertRow(r)

        c0 = data["image"] if data.get("type") == "image" else str(data["x"])
        c1 = "IMG" if data.get("type") == "image" else str(data["y"])

        self.grid.setItem(r, 0, QTableWidgetItem(c0))
        self.grid.setItem(r, 1, QTableWidgetItem(c1))
        self.grid.setItem(r, 2, QTableWidgetItem(str(data["delay"])))

        cb_btn = QComboBox()
        cb_btn.addItems(["left", "right", "middle"])
        cb_btn.setCurrentText(data["button"])
        self.grid.setCellWidget(r, 3, cb_btn)

        cb_tp = QComboBox()
        cb_tp.addItems(["single", "double", "hold"])
        cb_tp.setCurrentText(data["click_type"])
        self.grid.setCellWidget(r, 4, cb_tp)

    def toggle_rec(self):
        d = LANG_DATA.get(self.lang, LANG_DATA["English"])
        if self.rec_thread and self.rec_thread.isRunning():
            self.rec_thread.stop()
            self.rec_thread.wait()
            self.b_rec.setText(d["rec_start"])
            self.lbl_st.setText(d["st_stop"])
        else:
            self.clear_grid()
            self.rec_thread = InputRecorder()
            self.rec_thread.event_captured.connect(self.push_row)
            self.rec_thread.start()
            self.b_rec.setText(d["rec_stop"])
            self.lbl_st.setText(d["st_rec"])

    def delete_row(self):
        curr = self.grid.currentRow()
        if curr >= 0:
            self.grid.removeRow(curr)

    def clear_grid(self):
        self.grid.setRowCount(0)

    def extract_grid_data(self):
        res = []
        for r in range(self.grid.rowCount()):
            v0 = self.grid.item(r, 0).text()
            v1 = self.grid.item(r, 1).text()
            t_del = float(self.grid.item(r, 2).text())
            btn = self.grid.cellWidget(r, 3).currentText()
            tp = self.grid.cellWidget(r, 4).currentText()

            is_img = (v1 == "IMG")
            res.append({
                "type": "image" if is_img else "click",
                "x": 0 if is_img else int(v0),
                "y": 0 if is_img else int(v1),
                "delay": t_del,
                "button": btn,
                "click_type": tp,
                "image": v0 if is_img else ""
            })
        return res

    def save_json(self):
        items = self.extract_grid_data()
        if not items:
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Сохранить профиль", "", "JSON (*.json)")
        if fname:
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2)

    def load_json(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Загрузить профиль", "", "JSON (*.json)")
        if fname:
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.clear_grid()
                    for row in data:
                        self.push_row(row)
            except Exception as e:
                d = LANG_DATA.get(self.lang, LANG_DATA["English"])
                QMessageBox.critical(self, d["err"], str(e))

    def start(self):
        items = self.extract_grid_data()
        d = LANG_DATA.get(self.lang, LANG_DATA["English"])
        if not items:
            QMessageBox.warning(self, d["err"], d["empty_err"])
            return

        cfg = {
            "rnd_xy": self.spn_r_xy.value(),
            "rnd_t": self.spn_r_t.value(),
            "mode": self.cbo_lim.currentIndex(),
            "max_val": self.spn_lim_v.value()
        }

        self.click_thread = ClickWorker(items, cfg)
        self.click_thread.finished.connect(self.stop)
        self.click_thread.start()

        self.b_start.setEnabled(False)
        self.b_stop.setEnabled(True)
        self.apply_lang()

    def stop(self):
        if self.click_thread and self.click_thread.isRunning():
            self.click_thread.stop()
            self.click_thread.wait()

        self.b_start.setEnabled(True)
        self.b_stop.setEnabled(False)
        self.apply_lang()

    def closeEvent(self, event):
        self.stop()
        if self.hk_thread:
            self.hk_thread.stop()
        if self.rec_thread:
            self.rec_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
