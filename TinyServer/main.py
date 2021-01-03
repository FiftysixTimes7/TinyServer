import ctypes
import os
import sys
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.config import ConfigParser
from kivy.logger import Logger, LoggerHistory
from kivy.resources import resource_add_path, resource_find
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.settings import SettingsWithNoMenu
from kivy.uix.textinput import TextInput

from backend import load_config, main

thread = threading.Thread(target=main)


def start_server(instance=None):
    global thread
    if thread.is_alive():
        Logger.info('Bottle: Bottle is running')
        return
    thread = threading.Thread(target=main)
    thread.start()
    Logger.info('Bottle: Started')


def stop_server(instance=None):
    global thread
    if not thread.is_alive():
        Logger.info('Bottle: Bottle isn\'t running')
        return

    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), exc)
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
    thread.join()
    Logger.info('Bottle: Stopped')


def restart_server(*args):
    load_config()
    stop_server()
    start_server()


class ServerSettings(BoxLayout):
    def __init__(self, **kwargs):
        super(ServerSettings, self).__init__(**kwargs)
        config = ConfigParser()
        config.read('serverconfig.ini')
        config.setdefaults('main', {
            'root': '/sdcard',
            'allow_uploads': False,
            'port': 11451
        })
        s = SettingsWithNoMenu()
        s.add_json_panel('Server', config, resource_find('settings.json'))
        s.on_config_change = restart_server
        self.add_widget(s)


class Output(TextInput):
    def __init__(self, **kwargs):
        super(Output, self).__init__(**kwargs)

        def update(dt):
            self.text = '\n'.join(
                reversed([x.getMessage() for x in LoggerHistory.history]))
        Clock.schedule_interval(update, 0.1)


class TinyServerApp(App):
    def on_start(self):
        start_server()

    def on_stop(self):
        stop_server()


if __name__ == '__main__':
    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))
    TinyServerApp().run()
