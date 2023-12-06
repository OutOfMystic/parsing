import json
import os
import datetime as dt

import dearpygui.dearpygui as dpg

from exec_tools.wctools.bot import wcsession, WCSession
from parse_module.console.base import print_cols

API_KEY = '9fc65d805944483cdabff31e52a7d475'
BASE_DELAY = 30


def log_result(user, screen_time, result):
    row = [user, screen_time, result]
    jsoned = json.dumps(row) + '\n'
    results_path = os.path.join('screen', 'results.log')
    with open(results_path, 'a') as f:
        f.write(jsoned)


class ScreenManager:
    def __init__(self, from_date, to_date, img_path=None, check_items_rate=1):
        self.check_items_rate = check_items_rate
        self.imgs_array = []
        self.penalties = {}
        self.good_times = {}
        self._texture_id = None
        self.img_path = img_path
        if not img_path:
            self.img_path = wcsession.get_screenshots_dir(from_date, to_date)
        self._format_imgs()
        self.load_logs()
        self.current_row = self.get_next()

    def __del__(self):
        if not isinstance(self.img_path, str):
            self.img_path.cleanup()

    def _format_imgs(self):
        if not isinstance(self.img_path, str):
            img_path = self.img_path.name
        else:
            img_path = self.img_path

        for date in os.listdir(img_path):
            date_path = os.path.join(img_path, date)
            for user in os.listdir(date_path):
                self.penalties[user] = 0
                self.good_times[user] = 0
                date_user_path = os.path.join(img_path, date_path, user)
                for num, screen_time in enumerate(os.listdir(date_user_path)):
                    if (num % self.check_items_rate) != 0:
                        continue
                    good_path = os.path.join(date_user_path, screen_time)
                    item = [user, screen_time, good_path, None]
                    self.imgs_array.append(item)
        self.imgs_array.sort(key = lambda row: row[0] + row[1])

    def load_logs(self):
        results_path = os.path.join('screen', 'results.log')
        if not os.path.exists(results_path):
            return
        with open(results_path, 'r') as f:
            payload = f.read()

        stored = {}
        for line in payload.split('\n'):
            try:
                user, date, result = json.loads(line)
                key = (user, date,)
                stored[key] = result
            except:
                pass

        for img_row in self.imgs_array:
            user, screen_time, _, _ = img_row
            key = (user, screen_time,)
            if key not in stored:
                continue
            result = stored[key]
            img_row[3] = result

    def get_next(self):
        while self.imgs_array:
            img_row = self.imgs_array.pop()
            user, screen_time, _, result = img_row
            if result is False:
                self.penalties[user] += BASE_DELAY * self.check_items_rate
            elif result is True:
                self.good_times[user] += BASE_DELAY * self.check_items_rate
            else:
                return img_row
        print('No screenshots left to check during the period')
        self.finish()

    def finish(self):
        summary = {user: [0, 0, 0] for user in self.penalties}
        for user, minutes in self.good_times.items():
            summary[user][0] = minutes
        for user, minutes in self.penalties.items():
            summary[user][1] = minutes
        for user, data in summary.items():
            if data[1]:
                reliability = data[0] / (data[1] + data[0]) * 1000
                reliability = int(reliability) / 100
                data[-1] = 100.0 - reliability
            data[0] = format_mins(data[0])
            data[1] = format_mins(data[1])

        print('Results are:')
        rows = []
        for user, data in summary.items():
            good, penalty, reliability = data
            row = (user, good, penalty, reliability)
            rows.append(row)
        print_cols(rows, (30, 17, 17, 5))

        if not isinstance(self.img_path, str):
            self.img_path.cleanup()
        dpg.stop_dearpygui()

    def bad_img_button(self):
        user, screen_time, path, _ = self.current_row
        self.penalties[user] += BASE_DELAY * self.check_items_rate
        log_result(user, screen_time, False)
        self.current_row = self.get_next()
        new_user, _, new_path, _ = self.current_row
        if new_user != user:
            self.stop()
            self.start(first=False)
        self.set_image(new_path)
        print(f'{len(self.imgs_array)} left')

    def good_img_button(self):
        user, screen_time, path, _ = self.current_row
        self.penalties[user] += BASE_DELAY * self.check_items_rate
        log_result(user, screen_time, True)
        self.current_row = self.get_next()
        new_user, _, new_path, _ = self.current_row
        if new_user != user:
            self.stop()
            self.start(first=False)
        self.set_image(new_path)
        print(f'{len(self.imgs_array)} left')

    def set_image(self, path):
        width, height, channels, data = dpg.load_image(path)
        dpg.set_value(self._texture_id, data)

    def stop(self):
        dpg.stop_dearpygui()
        dpg.delete_item('wnd')

    def start(self, first=True):
        dpg.create_context()

        width, height, channels, data = dpg.load_image(self.current_row[2])

        with dpg.texture_registry():
            self._texture_id = dpg.add_dynamic_texture(width=width, height=height, default_value=data)

        with dpg.window(label="Screen Checker wnd", tag='wnd'):
            dpg.add_image(self._texture_id, width=width, height=height)
            group = dpg.add_group(horizontal=True)
            dpg.add_button(label="Bad", callback=self.bad_img_button, parent=group)
            dpg.add_button(label="Good", callback=self.good_img_button, parent=group)

        dpg.create_viewport(title='Screen Checker', width=1100, height=700)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()


def format_mins(mins):
    hours = mins // 60
    mins = mins % 60
    return f'{hours} hrs, {mins} mins'


if __name__ == '__main__':
    session = WCSession()
    session.login()
    # dir_ = session.get_screenshots_dir(dt.datetime(year=2023, month=1, day=26),
    #                                    dt.datetime(year=2023, month=1, day=27))
    manager = ScreenManager(dt.datetime(year=2023, month=2, day=1),
                            dt.datetime(year=2023, month=3, day=1),
                            img_path=r'C:\Users\ibrag\Downloads\tmp2jsdeof9')
    manager.start()
