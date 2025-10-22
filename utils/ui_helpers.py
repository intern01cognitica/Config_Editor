# ---------------- STYLED WIDGET HELPERS ----------------
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.graphics import Color,Rectangle, RoundedRectangle,Line
from kivy.clock import Clock
from kivy.uix.image import Image
import os

loading_popup = None  
loading_popup = None  

def show_loading(message="Please wait..."):
    """Show a modal popup styled like show_popup, but without a close button."""
    global loading_popup
    if loading_popup:
        return  # already showing

    # Message label
    message_label = Label(
        text=message,
        color=(0, 0, 0, 1),
        font_size='18sp',
        halign="center",
        valign="middle",
        text_size=(dp(400), None),
        size_hint=(None, None)
    )
    message_label.bind(texture_size=lambda inst, val: setattr(inst, "size", val))

    # Layout (no close button here)
    layout = BoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(10),
        size_hint=(None, None)
    )
    layout.add_widget(message_label)

    def open_popup(*_):
        popup_width = message_label.texture_size[0] + dp(80)
        popup_height = message_label.texture_size[1] + dp(120)
        layout.size = (popup_width, popup_height)

        popup = Popup(
            title='',
            separator_height=0,
            content=layout,
            size_hint=(None, None),
            size=(popup_width, popup_height),
            background='',
            background_color=(1, 1, 1, 1),
            auto_dismiss=False  # can't close manually
        )

        # store reference globally
        global loading_popup
        loading_popup = popup
        popup.open()

    Clock.schedule_once(open_popup, 0)


def hide_loading(*args):
    """Hide the loading popup if visible."""
    global loading_popup
    if loading_popup:
        loading_popup.dismiss()
        loading_popup = None

        
class LimitedSpinnerOption(SpinnerOption):
    """Base option style"""
    pass


class CustomLimitedSpinnerOption(LimitedSpinnerOption):
    """Styled dropdown option with white background and black border outline"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0, 0, 0, 1)  # black text
        self.font_size = '16sp'
        self.height = dp(50)
        self.text_size = (dp(220), None)
        self.halign = 'center'
        self.valign = 'middle'
        self.shorten = True
        self.shorten_from = 'right'

        with self.canvas.before:
            # White background
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(10)]
            )

        with self.canvas.after:
            # Black border outline
            Color(0, 0, 0, 1)
            self.border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)),
                width=1.2
            )

        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        # Update background position/size
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

        # Update border line to match
        self.border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(10)
        )



class RoundedButton(Button):
    """Rounded button with customizable bg color"""
    def __init__(self, bg_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0, 0, 0, 1)
        with self.canvas.before:
            Color(*bg_color)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(20)])
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


def show_popup(message, reset=None):
    # Message label
    message_label = Label(
        text=message,
        color=(0, 0, 0, 1),
        font_size='18sp',
        halign="center",
        valign="middle",
        text_size=(dp(400), None),
        size_hint=(None, None)
    )
    message_label.bind(texture_size=lambda inst, val: setattr(inst, "size", val))

    # Close button
    close_btn = Button(
        text="X",
        size_hint=(None, None),
        size=(dp(40), dp(40)),
        background_normal="",
        background_color=(1, 0, 0, 0.8),
        color=(1, 1, 1, 1),
        bold=True,
        pos_hint={"right": 1, "top": 1}
    )

    # Layout
    layout = BoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(10),
        size_hint=(None, None)
    )
    layout.add_widget(close_btn)
    layout.add_widget(message_label)

    def open_popup(*_):
        popup_width = message_label.texture_size[0] + dp(80)
        popup_height = message_label.texture_size[1] + dp(120)
        layout.size = (popup_width, popup_height)

        popup = Popup(
            title='',
            separator_height=0,
            content=layout,
            size_hint=(None, None),
            size=(popup_width, popup_height),
            background='',
            background_color=(1, 1, 1, 1),
            auto_dismiss=False
        )

        def on_close(*_):
            popup.dismiss()
            if reset:
                reset()

        close_btn.bind(on_release=on_close)
        popup.open()

    Clock.schedule_once(open_popup, 0)
def dropdown_icon(spinner):
    """Attach a dropdown icon to any spinner."""
    base_dir = os.path.dirname(__file__)
    icon_path = os.path.join(base_dir, "dropdown_icon.png")

    dropdown_icon = Image(
        source=icon_path,
        size_hint=(None, None),
        size=(16, 16)
    )

    def position_dropdown_icon(instance, value):
        dropdown_icon.pos = (
            instance.x + instance.width - 32,
            instance.y + (instance.height - 16) / 2
        )

    spinner.add_widget(dropdown_icon)
    spinner.bind(pos=position_dropdown_icon, size=position_dropdown_icon)
