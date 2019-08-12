from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout

from kivymd.theming import ThemeManager


class Interface(FloatLayout):
    pass


class Test(App):
    theme_cls = ThemeManager()
    theme_cls.primary_palette = 'Indigo'
    theme_cls.accent_palette = 'Indigo'
    def build(self):
        return Interface()


if __name__ == '__main__':
    Test().run()