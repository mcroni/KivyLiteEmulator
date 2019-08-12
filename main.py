import os
import sys
original_argv = sys.argv
import traceback
from fnmatch import fnmatch
from functools import partial
from importlib import reload
from logging import Logger
from os.path import join, realpath
from threading import Thread
from kivy.app import App
from kivy.clock import mainthread, Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, NumericProperty, StringProperty, ListProperty
from kivy.resources import resource_add_path, resource_remove_path
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from monotonic import monotonic

from kivymd.theming import ThemeManager
from plyer import filechooser


class EmulatorScreen(Screen):
    pass


class HistoryScreen(Screen):
    pass


class EmuInterface(FloatLayout):
    pass



def toast(text):
    from kivymd.toast.kivytoast import toast
    toast(text)

class KivyEmu(App):
    theme_cls = ThemeManager()
    theme_cls.primary_palette = 'Indigo'
    theme_cls.accent_palette = 'Indigo'
    Window.size = (300, 650)
    filename = None
    class_name = None
    selection = ListProperty([])
    bs_menu_1 = None
    # reloader = ReloaderApp()

    AUTORELOADER_PATHS = [
        (".", {"recursive": True}),
    ]

    AUTORELOADER_IGNORE_PATTERNS = [
        "*.pyc", "*__pycache__*"
    ]

    KV_FILES = [

    ]
    CLASSES = {}
    def get_root(self):
        """
        Return a root widget, that will contains your application.
        It should not be your application widget itself, as it may
        be destroyed and recreated from scratch when reloading.

        By default, it returns a RelativeLayout, but it could be
        a Viewport.
        """
        return Factory.RelativeLayout()

    def build_app(self, first=False):
        """Must return your application widget.

        If `first` is set, it means that will be your first time ever
        that the application is built. Act according to it.
        """
        raise NotImplemented()

    def unload_app_dependencies(self):
        """
        Called when all the application dependencies must be unloaded.
        Usually happen before a reload
        """
        for path in self.KV_FILES:
            path = realpath(path)
            Builder.unload_file(path)
        for name, module in self.CLASSES.items():
            Factory.unregister(name)

    def load_app_dependencies(self):
        """
        Load all the application dependencies.
        This is called before rebuild.
        """
        for path in self.KV_FILES:
            path = realpath(path)
            Builder.load_file(path)
        for name, module in self.CLASSES.items():
            Factory.register(name, module=module)

    def rebuild(self, *largs, **kwargs):
        print("rebuildig application")
        self.emulate_file(self.filename)
        print("done reloading")
        # Logger.debug("{}: Rebuild the application".format(self.appname))
        # first = kwargs.get("first", False)
        # try:
        #     if not first:
        #         self.unload_app_dependencies()
        #     self.load_app_dependencies()
        #     self.set_widget(None)
        #
        #     self.start_emulation()
        # except Exception as e:
        #     pass
            # self.approot = self.build_app()
            # self.root.ids.emulator_screen =
        #     self.set_widget(self.approot)
        #     self.apply_state(self.state)
        # except Exception as e:
        #     import traceback
        #     Logger.exception("{}: Error when building app".format(self.appname))
        #     self.set_error(repr(e), traceback.format_exc())
        #     if not self.DEBUG and self.RAISE_ERROR:
        #         raise

    @mainthread
    def set_error(self, exc, tb=None):
        print(tb)
        from kivy.core.window import Window
        lbl = Factory.Label(
            text_size=(Window.width - 100, None),
            text="{}\n\n{}".format(exc, tb or ""))
        self.set_widget(lbl)

    def bind_key(self, key, callback):
        """
        Bind a key (keycode) to a callback
        (cannot be unbind)
        """
        from kivy.core.window import Window

        def _on_keyboard(window, keycode, *largs):
            if key == keycode:
                return callback()

        Window.bind(on_keyboard=_on_keyboard)

    @property
    def appname(self):
        """
        Return the name of the application class
        """
        return self.__class__.__name__

    def enable_autoreload(self):
        """
        Enable autoreload manually. It is activated automatically
        if "DEBUG" exists in environ.

        It requires the `watchdog` module.
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            Logger.warn("{}: Autoreloader is missing watchdog".format(self.appname))
            return
        # Logger.info(" Autoreloader activated")
        print("Autoreload activated")
        rootpath = self.get_root_path()
        # print("this is the root path",rootpath)
        self.w_handler = handler = FileSystemEventHandler()
        handler.dispatch = self._reload_from_watchdog
        self._observer = observer = Observer()
        for path in self.AUTORELOADER_PATHS:
            # print(path,"paths dey")
            options = {"recursive": True}
            if isinstance(path, (tuple, list)):
                # print("iii")
                path, options = path
            observer.schedule(
                handler, join(rootpath, path),
                **options)
        observer.start()

    @mainthread
    def _reload_from_watchdog(self, event):
        from watchdog.events import FileModifiedEvent
        if not isinstance(event, FileModifiedEvent):
            return

        for pat in self.AUTORELOADER_IGNORE_PATTERNS:
            if fnmatch(event.src_path, pat):
                return

        if event.src_path.endswith(".py"):
            # source changed, reload it
            try:
                Builder.unload_file(event.src_path)
                self._reload_py(event.src_path)
            except Exception as e:
                import traceback
                self.set_error(repr(e), traceback.format_exc())
                return

        if event.src_path.endswith(".kv"):
            origin = str(event.src_path).split('.')
            main_path = str(event.src_path).split('\\')[:-1]
            main_path = "\\".join(main_path)
            print(main_path)
            if 'main.py' in os.listdir(main_path):
                new_path = os.path.join(main_path,'main.py')
                try:
                    Builder.unload_file(new_path)
                    self._reload_py(new_path)
                except Exception as e:
                    import traceback
                    self.set_error(repr(e), traceback.format_exc())
                    return

        print("reload cause of", event)
        print(event.src_path, "this is the file that caused the reload")
        print(self.filename,"this is the original filename")
        Clock.unschedule(self.rebuild)
        Clock.schedule_once(self.rebuild, 0.1)

    def _reload_py(self, filename):
        # we don't have dependency graph yet, so if the module actually exists
        # reload it.

        filename = realpath(filename)
        print("filename from realpath")
        # check if it's our own application file
        try:
            mod = sys.modules[self.__class__.__module__]
            mod_filename = realpath(mod.__file__)
        except Exception as e:
            mod_filename = None

        # detect if it's the application class // main
        if mod_filename == filename:
            return self._restart_app(mod)

        module = self._filename_to_module(filename)
        if module in sys.modules:
            Logger.debug("{}: Module exist, reload it".format(self.appname))
            Factory.unregister_from_filename(filename)
            self._unregister_factory_from_module(module)
            reload(sys.modules[module])

    def _unregister_factory_from_module(self, module):
        # check module directly
        to_remove = [
            x for x in Factory.classes
            if Factory.classes[x]["module"] == module]

        # check class name
        for x in Factory.classes:
            cls = Factory.classes[x]["cls"]
            if not cls:
                continue
            if getattr(cls, "__module__", None) == module:
                to_remove.append(x)

        for name in set(to_remove):
            del Factory.classes[name]

    def _filename_to_module(self, filename):
        orig_filename = filename
        rootpath = self.get_root_path()
        if filename.startswith(rootpath):
            filename = filename[len(rootpath):]
        if filename.startswith("/"):
            filename = filename[1:]
        module = filename[:-3].replace("/", ".")
        print("translated to",orig_filename,module)
        # Logger.debug("{}: Translated {} to {}".format(self.appname, orig_filename, module))
        return module

    def _restart_app(self, mod):
        _has_execv = sys.platform != 'win32'
        cmd = [sys.executable] + original_argv
        if not _has_execv:
            import subprocess
            subprocess.Popen(cmd)
            sys.exit(0)
        else:
            try:
                os.execv(sys.executable, cmd)
            except OSError:
                os.spawnv(os.P_NOWAIT, sys.executable, cmd)
                os._exit(0)

    def prepare_foreground_lock(self):
        """
        Try forcing app to front permanently to avoid windows
        pop ups and notifications etc.app

        Requires fake fullscreen and borderless.

        .. note::

            This function is called automatically if `FOREGROUND_LOCK` is set

        """
        try:
            import ctypes
            LSFW_LOCK = 1
            ctypes.windll.user32.LockSetForegroundWindow(LSFW_LOCK)
            Logger.info("App: Foreground lock activated")
        except Exception:
            Logger.warn("App: No foreground lock available")

    def set_widget(self, wid):
        """
        Clear the root container, and set the new approot widget to `wid`
        """
        self.root.clear_widgets()
        self.approot = wid
        if wid is None:
            return
        self.root.add_widget(self.approot)
        try:
            wid.do_layout()
        except Exception:
            pass

    def get_root_path(self):
        """
        Return the root file path
        """
        return realpath(os.getcwd())

    # State management
    def apply_state(self, state):
        """Whatever the current state is, reapply the current state
        """
        pass

    # Idle management leave
    def install_idle(self, timeout=60):
        """
        Install the idle detector. Default timeout is 60s.
        Once installed, it will check every second if the idle timer
        expired. The timer can be rearm using :func:`rearm_idle`.
        """
        if monotonic is None:
            Logger.exception("{}: Cannot use idle detector, monotonic is missing".format(self.appname))
        self.idle_timer = None
        self.idle_timeout = timeout
        Clock.schedule_interval(self._check_idle, 1)
        self.root.bind(
            on_touch_down=self.rearm_idle,
            on_touch_up=self.rearm_idle)

    def _check_idle(self, *largs):
        if not hasattr(self, "idle_timer"):
            return
        if self.idle_timer is None:
            return
        if monotonic() - self.idle_timer > self.idle_timeout:
            self.idle_timer = None
            self.dispatch("on_idle")

    def rearm_idle(self, *largs):
        """
        Rearm the idle timer
        """
        if not hasattr(self, "idle_timer"):
            return
        if self.idle_timer is None:
            self.dispatch("on_wakeup")
        self.idle_timer = monotonic()

    def on_idle(self, *largs):
        """
        Event fired when the application enter the idle mode
        """
        pass

    def on_wakeup(self, *largs):
        """
        Event fired when the application leaves idle mode
        """
        pass

    # internals
    def patch_builder(self):
        Builder.orig_load_string = Builder.load_string
        Builder.load_string = self._builder_load_string

    def _builder_load_string(self, string, **kwargs):
        if "filename" not in kwargs:
            from inspect import getframeinfo, stack
            caller = getframeinfo(stack()[1][0])
            kwargs["filename"] = caller.filename
        return Builder.orig_load_string(string, **kwargs)


    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def watchdog_reloader(self,args):
        print("reloading begins ")
        # self.AUTORELOADER_PATHS = self.AUTORELOADER_PATHS
        self.enable_autoreload()
        self.patch_builder()
        
    def choose(self):
        filechooser.open_file(on_selection=self.handle_selection)

    def handle_selection(self, selection):
        self.selection = selection

    def on_selection(self, *a, **k):
        self.clear()

    def clear(self):
        try:
            self.root.ids.emulator_screen.clear_widgets()
            Window.borderless = True
            Clock.schedule_once(self.watchdog_reloader, 2)
            self.filename = str(self.selection[0])
            base = "\\".join(self.filename.split("\\")[:-1])
            print(base)
            self.AUTORELOADER_PATHS.clear()
            self.AUTORELOADER_PATHS.append((base, {"recursive": True}))
            self.emulate_file(self.selection[0])
            print(self.AUTORELOADER_PATHS)
        except:
            pass

    def build(self):
        return EmuInterface()

    def emulate_file(self, filename, threaded=False):
        root = None
        if not os.path.exists(filename):
            return

        dirname = os.path.dirname(filename)
        sys.path.append(dirname)
        os.chdir(dirname)
        resource_add_path(dirname)

        # self.root.ids.emulator_screen.clear_widgets()

        if threaded:
            Thread(target=partial(self.start_emulation, filename, threaded=threaded)).start()
        else:
            self.start_emulation(filename, threaded=threaded)

    def start_emulation(self, filename, threaded=False):
        print("___________________________________")
        print("Starting thread")
        root = None
        # print(os.path.splitext(filename))
        if os.path.splitext(filename)[1] == '.kv':  # load the kivy file directly
            try:  # cahching error with kivy files
                Builder.unload_file(filename)
                # print("unloaded the kv")
                root = Builder.load_file(filename)
            except:
                traceback.print_exc()
                print("You kivy file has a problem")

        elif os.path.splitext(filename)[1] == '.py':
            print("its a py")
            self.load_defualt_kv(filename)

            try:  # cahching error with python files
                root = self.load_py_file(filename)
            except:
                traceback.print_exc()
                print("You python file has a problem")

        if root:
            print("this is the root",root)
            if threaded:
                self.emulation_done(root, filename)
            else:
                print("not threaded")
                self.root.ids.emulator_screen.clear_widgets()
                self.root.ids.emulator_screen.add_widget(root)

        dirname = os.path.dirname(filename)
        sys.path.pop()
        resource_remove_path(dirname)

    @mainthread
    def emulation_done(self, root, filename):
        if root:
            self.root.ids.emulator_screen.add_widget(root)

    def load_defualt_kv(self, filename):
        app_cls_name = self.get_app_cls_name(filename)
        self.class_name = app_cls_name
        if app_cls_name is None:
            return

        kv_name = app_cls_name.lower()
        if app_cls_name.endswith('App'):
            kv_name = app_cls_name[:len(app_cls_name) - 3].lower()
        if app_cls_name:
            file_dir = os.path.dirname(filename)
            kv_filename = os.path.join(file_dir, kv_name + '.kv')
            print(kv_filename)
            if os.path.exists(kv_filename):
                try:  # cahching error with kivy files
                    Builder.unload_file(kv_filename)
                    print("unloaded the kv file ")
                    # self.root.ids.emulator_screen.clear_widgets()
                    print("clearing the emulator screen here")
                    # self.root.ids.emulator_screen.clear_widgets()
                    root = Builder.load_file(kv_filename)
                except:
                    traceback.print_exc()
                    print("You kivy file has a problem")

    def get_app_cls_name(self, filename):
        with open(filename) as fn:
            text = fn.read()

        lines = text.splitlines()
        app_cls = self.get_import_as('from kivy.app import App', lines)

        def check_app_cls(line):
            line = line.strip()
            return line.startswith('class') and line.endswith('(%s):' % app_cls)

        found = list(filter(check_app_cls, lines))

        if found:
            line = found[0]
            cls_name = line.split('(')[0].split(' ')[1]
            return cls_name

    def get_root_from_runTouch(self,filename):
        with open(filename) as fn:
            text = fn.read()

        lines = text.splitlines()
        run_touch = self.get_import_as('from kivy.base import runTouchApp', lines)

        def check_run_touch(line):
            line = line.strip()
            return line.startswith('%s(' % run_touch)

        found = list(filter(check_run_touch, lines))

        if found:
            line = found[0]
            root_name = line.strip().split('(')[1].split(')')[0]
            root_file = self.import_from_dir(filename)
            root = getattr(reload(root_file), root_name)

            return root

    def load_py_file(self, filename):
        app_cls_name = self.get_app_cls_name(filename)
        if app_cls_name:
            root_file = self.import_from_dir(filename)
            app_cls = getattr(reload(root_file), app_cls_name)
            root = app_cls().build()

            return root

        run_root = self.get_root_from_runTouch(filename)
        if run_root:
            return run_root

    def import_from_dir(self, filename):
        ''' force python to import this file
        from the project_ dir'''

        dirname, file = os.path.split(filename)
        sys.path = [dirname] + sys.path

        import_word = os.path.splitext(file)[0]
        imported = __import__(import_word)
        return imported

    def get_import_as(self, start, lines):
        line = list(filter(lambda line: line.strip().startswith(start), lines))
        if line:
            words = line[0].split(' ')
            import_word = words[len(words) - 1]
            return import_word
        else:
            return

    def callback_for_menu_items(self, *args):
        toast(args[0])

    def show_example_bottom_sheet(self):
        from kivymd.bottomsheet import MDListBottomSheet
        if not self.bs_menu_1:
            self.bs_menu_1 = MDListBottomSheet()
            self.bs_menu_1.add_item(
                "Open File",
                lambda x: self.choose(),
                icon='file')
            self.bs_menu_1.add_item(
                "Open History Tab",
                lambda x: self.history_screen(),
                icon='history')
            self.bs_menu_1.add_item(
                "Close Emulator",
                lambda x: self.stop(),
                icon='window-close')
        self.bs_menu_1.open()

    def history_screen(self):
        pass


if __name__ == '__main__':
    KivyEmu().run()
