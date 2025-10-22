# ---------------- LOGIN SCREEN ----------------
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from utils.ui_helpers import show_popup,RoundedButton
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Main vertical layout
        layout = BoxLayout(orientation="vertical", padding=100, spacing=50)

        # --- Top section (title + inputs) ---
        top_layout = BoxLayout(orientation="vertical", spacing=60, size_hint=(1, 0.5))
        login_label = Label(text="Login", font_size=22, color=(0, 0, 0, 1))
        top_layout.add_widget(login_label)

        # ✅ Define text inputs before adding
        self.username = TextInput(
            hint_text="Username", multiline=False,
            size_hint=(None, None), size=(dp(200), dp(45)),
            pos_hint={"center_x": 0.5},
            font_size='20sp'
        )
        self.password = TextInput(
            hint_text="Password", multiline=False, password=True,
            size_hint=(None, None), size=(dp(200), dp(45)),
            pos_hint={"center_x": 0.5},
            font_size='20sp'
        )

        # Group username & password into a smaller layout
        inputs_layout = BoxLayout(orientation="vertical", spacing=15, size_hint=(1, None))
        inputs_layout.add_widget(self.username)
        inputs_layout.add_widget(self.password)

        top_layout.add_widget(inputs_layout)

        # --- Bottom section (buttons) ---
        bottom_layout = BoxLayout(orientation="vertical", spacing=25, size_hint=(1, 0.4))
        login_btn = RoundedButton(
            text="Login as Admin",
            size_hint=(None, None),
            size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            bg_color=(0.0, 0.67, 0.93, 1),
            font_size='18sp' # blue
        )
        login_btn.bind(on_release=self.authenticate)

        user_btn = RoundedButton(
            text="Continue as User",
            size_hint=(None, None),
            size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            bg_color=(1, 1, 1, 1),
            font_size='18sp'# white
        )
        user_btn.bind(on_release=lambda x: setattr(self.manager, "current", "user"))

        bottom_layout.add_widget(login_btn)
        bottom_layout.add_widget(user_btn)

        # Add everything to main layout
        layout.add_widget(top_layout)
        layout.add_widget(bottom_layout)

        self.add_widget(layout)

    def authenticate(self, instance):
        if self.username.text == "cai-admin" and self.password.text == "Cogn!@2023":
            self.manager.get_screen("admin").load_data()
            self.manager.current = "admin"
        else:
            show_popup("Invalid username or password")