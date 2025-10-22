from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.metrics import dp
from kivy.graphics import Color,Rectangle, RoundedRectangle,Line
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.metrics import dp
import os
import re
import subprocess
import yaml
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

YAML_PATH = "conc.yaml"

yaml_ruamel = YAML()
yaml_ruamel.preserve_quotes = True


# ---------------- YAML HELPERS ----------------
def load_yaml_preserve():
    if os.path.exists(YAML_PATH):
        with open(YAML_PATH, 'r') as f:
            return yaml_ruamel.load(f)
    return {}


def save_yaml_preserve(data):
    with open(YAML_PATH, 'w') as f:
        yaml_ruamel.dump(data, f)
def update_yaml_line(file_path, key_path, new_value):
    """
    Update a YAML key in-place (line-based).
    key_path: dotted string like 'serial.enable_Failsafe' or 'background_p0.threshold'
    new_value: written as-is (no formatting changes).
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    parts = key_path.split(".")
    updated = False
    indent_level = 0

    for i, line in enumerate(lines):
        # Match parent section
        if len(parts) > 1 and re.match(rf"^\s*{re.escape(parts[0])}\s*:", line):
            indent_level = len(line) - len(line.lstrip()) + 2

        # Match final key
        final_key = parts[-1]
        pattern = rf"^(\s*){re.escape(final_key)}\s*:\s*.*$"
        if re.match(pattern, line):
            indent = " " * (len(line) - len(line.lstrip()))
            lines[i] = f"{indent}{final_key}: {new_value}\n"
            updated = True
            break

    if updated:
        with open(file_path, "w") as f:
            f.writelines(lines)
    else:
        raise KeyError(f"Key {key_path} not found in {file_path}")
def format_points(points):
    outer = CommentedSeq()
    for p in points:
        inner = CommentedSeq(p)
        inner.fa.set_flow_style()
        outer.append(inner)
    return outer
def update_config_for_camera(cam_index):
    yaml = YAML()
    yaml.preserve_quotes = True

    # --- Load config.yaml ---
    with open("config.yaml", "r") as f:
        cfg = yaml.load(f)

    # --- Load conc.yaml ---
    with open("conc.yaml", "r") as f:
        conc = yaml.load(f)

    # ✅ Update cam_id
    cfg["cam_id"] = cam_index

    # ✅ Build full RTSP URL with enforced double quotes
    cam_key = f"background_p{cam_index}"
    if cam_key in conc:
        ip_path = conc[cam_key].get("ip_address")  # e.g. 192.168.1.250:554/Streaming/Channels/102
        if ip_path:
            rtsp_prefix = "rtsp://admin:Cogn!@2023@"
            cfg["camera_pos"] = DoubleQuotedScalarString(rtsp_prefix + ip_path)

    # --- Save config.yaml back (preserve formatting & comments) ---
    with open("config.yaml", "w") as f:
        yaml.dump(cfg, f)
def save_points_to_config(cam_index, points):
    yaml = YAML()
    yaml.preserve_quotes = True

    with open("config.yaml", "r") as f:
        cfg = yaml.load(f)

    key = f"p{cam_index}_zone_coords"
    if key not in cfg:
        cfg[key] = {"red": [], "orange": [], "blue": [], "line_thickness": 2, "num_zones": 1}

    # ✅ Convert each point into flow-style list
    red_points = []
    for pt in points:
        seq = CommentedSeq(pt)
        seq.fa.set_flow_style()   # force [x, y] style
        red_points.append(seq)

    cfg[key]["red"] = red_points
    cfg[key]["orange"] = []
    cfg[key]["blue"] = []
    cfg[key]["num_zones"] = 1
    cfg[key]["line_thickness"] = 2

    with open("config.yaml", "w") as f:
        yaml.dump(cfg, f)

# ---------------- STYLED WIDGET HELPERS ----------------
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


# ---------------- LOGIN SCREEN ----------------
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

# ---------------- ADMIN SCREEN ----------------

class AdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {}

        # Root layout
        root = BoxLayout(orientation="vertical")

        # --- TOP CONTENT (Admin Panel, Params, Threshold) ---
        top_layout = BoxLayout(orientation="vertical", padding=300, spacing=80, size_hint=(1, 0.85))

        top_layout.add_widget(Label(text="Admin Panel", font_size=22, color=(0, 0, 0, 1)))

        # --- Grid for parameters ---
        grid = GridLayout(cols=2, spacing=120, size_hint=(1, None))
        grid.bind(minimum_height=grid.setter("height"))

        def param_box(label_text, widget):
            box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(60), spacing=10)

            lbl = Label(
                text=label_text,
                color=(0, 0, 0, 1),
                size_hint=(None, None),
                size=(dp(200), dp(50)),
                halign="right",
                valign="middle",
                font_size="18sp" 
            )
            lbl.bind(size=lambda inst, val: setattr(inst, "text_size", inst.size))

            box.add_widget(lbl)
            box.add_widget(widget)
            return box

        # Number of Cameras spinner
        self.num_cam_spinner = Spinner(
            text="", values=["4", "6"],
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            option_cls=CustomLimitedSpinnerOption
        )
        grid.add_widget(param_box("Number of Cameras:", self.num_cam_spinner))

        # Failsafe
        self.failsafe_spinner = Spinner(
            text="Enable", values=["Enable", "Disable"],
            size_hint=(None, None), size=(dp(200), dp(50)),
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        grid.add_widget(param_box("Failsafe:", self.failsafe_spinner))

        # Interlock
        self.interlock_spinner = Spinner(
            text="Enable", values=["Enable", "Disable"],
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        grid.add_widget(param_box("Interlock :", self.interlock_spinner))

        # Camera Selection
        self.camera_spinner = Spinner(
            text="Camera 0", values=[f"Camera {i}" for i in range(6)],
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        self.camera_spinner.dropdown_cls.max_height = dp(120)
        self.camera_spinner.bind(text=self.on_camera_change)
        grid.add_widget(param_box("Camera Selection:", self.camera_spinner))

        top_layout.add_widget(grid)

        # --- Threshold centered below ---
        threshold_anchor = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, None), height=dp(100))
        threshold_box = BoxLayout(orientation="horizontal", spacing=10, size_hint=(None, None))
        threshold_box.size = (dp(300), dp(40))

        threshold_box.add_widget(Label(text="Threshold:", color=(0, 0, 0, 1), size_hint=(None, None), size=(dp(100), dp(40)),font_size='18sp',))

        self.threshold_input = TextInput(
            multiline=False,
            size_hint=(None, None),
            size=(dp(150), dp(40)),
            halign="center",
            background_normal='', background_active='',
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            font_size='18sp'
        )
        self.threshold_input.bind(size=lambda inst, val: setattr(inst, "text_size", inst.size))

        threshold_box.add_widget(self.threshold_input)
        threshold_anchor.add_widget(threshold_box)
        top_layout.add_widget(threshold_anchor)

        # Add top section to root
        root.add_widget(top_layout)

        # --- BOTTOM BUTTONS ---
        bottom_layout = BoxLayout(orientation="vertical", spacing=40, padding=150, size_hint=(1, 0.15))

        save_btn = RoundedButton(
            text="Save", size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5}, bg_color=(0.0, 0.67, 0.93, 1),font_size='18sp'
        )
        save_btn.bind(on_release=self.save_data)

        logout_btn = RoundedButton(
            text="Logout", size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5}, bg_color=(1, 1, 1, 1),font_size='18sp'
        )
        logout_btn.bind(on_release=lambda x: setattr(self.manager, "current", "login"))

        bottom_layout.add_widget(save_btn)
        bottom_layout.add_widget(logout_btn)

        # Add bottom section to root
        root.add_widget(bottom_layout)

        # Add everything to screen
        self.add_widget(root)

    def on_camera_change(self, spinner, text):
        """Update threshold when user selects a different camera."""
        try:
            cam_index = int(text.split(" ")[-1])-1
            key = f"background_p{cam_index}"
            self.threshold_input.text = str(self.data.get(key, {}).get("threshold", ""))
        except Exception:
            self.threshold_input.text = ""

    def load_data(self):
        self.data = load_yaml_preserve()
        self.failsafe_spinner.text = "Enable" if self.data.get("serial", {}).get("enable_Failsafe", 0) == 1 else "Disable"
        self.interlock_spinner.text = "Enable" if self.data.get("serial", {}).get("enable_brake", 0) == 1 else "Disable"

        # ✅ Fetch num_cam from YAML (default 4 if missing)
        num_cam = str(self.data.get("serial", {}).get("num_cam", 4))
        if num_cam not in ["4", "6"]:  
            num_cam = "4"
        self.num_cam_spinner.text = num_cam

        # ✅ Update camera spinner dynamically
        self.camera_spinner.values = [f"Camera {i}" for i in range(int(num_cam))]
        self.camera_spinner.text = "Camera 0"

        self.threshold_input.text = str(self.data.get("background_p0", {}).get("threshold", ""))


    def save_data(self, instance):
        try:
            if "serial" not in self.data:
                self.data["serial"] = {}

            # ✅ Which camera is selected?
            cam_index = int(self.camera_spinner.text.split(" ")[-1])
            key = f"background_p{cam_index}"
            if key not in self.data:
                self.data[key] = {}

            # Save global settings
            self.data["serial"]["enable_Failsafe"] = 1 if self.failsafe_spinner.text == "Enable" else 0
            self.data["serial"]["enable_brake"] = 1 if self.interlock_spinner.text == "Enable" else 0

            # ✅ Save threshold for the selected camera
            self.data[key]["threshold"] = float(self.threshold_input.text.strip())

            # Save number of cameras
            num_cam = int(self.num_cam_spinner.text)
            self.data["serial"]["num_cam"] = num_cam

            # ✅ Immediately update the camera spinner options
            self.camera_spinner.values = [f"Camera {i}" for i in range(num_cam)]
            if cam_index >= num_cam:
                self.camera_spinner.text = "Camera 0"  # reset if current selection is invalid

            save_yaml_preserve(self.data)
            show_popup(f"Settings Updated")
        except Exception as e:
            show_popup(str(e))


# ---------------- USER SCREEN ----------------
class UserScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {}

        # Root layout
        root = BoxLayout(orientation="vertical")

        # --- TOP CONTENT (User Panel, Zone Selection, Zone Points) ---
        top_layout = BoxLayout(orientation="vertical", padding=300, spacing=60, size_hint=(1, 0.85))
        top_layout.add_widget(Label(text="User Panel", font_size=22, color=(0, 0, 0, 1)))

        # --- Grid for parameters (1 column) ---
        grid = GridLayout(cols=1, spacing=80, size_hint=(1, None))
        grid.bind(minimum_height=grid.setter("height"))

        def param_box(label_text, widget, box_width=400, box_height=60):
            # AnchorLayout ensures centering
            wrapper = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, None), height=dp(box_height))

            # Inner horizontal box, fixed size
            box = BoxLayout(
                orientation="horizontal",
                spacing=10,
                size_hint=(None, None),
                size=(dp(box_width), dp(box_height))
            )

            lbl = Label(
                text=label_text,
                color=(0, 0, 0, 1),
                size_hint=(None, None),
                size=(dp(150), dp(40)),
                halign="right",
                valign="middle",
                font_size="18sp" 
            )
            lbl.bind(size=lambda inst, val: setattr(inst, "text_size", inst.size))

            box.add_widget(lbl)
            box.add_widget(widget)

            wrapper.add_widget(box)
            return wrapper



        # --- Zone Selection spinner ---
        self.zone_spinner = Spinner(
            text="Camera 0",
            values=[f"Camera {i}" for i in range(6)],
            size_hint=(None, None),
            size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption,
            background_normal='',
            background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1),
            font_size='18sp'
        )
        self.zone_spinner.dropdown_cls.max_height = dp(120)
        self.zone_spinner.bind(text=self.on_zone_change)
        grid.add_widget(param_box("Camera Selection:", self.zone_spinner))

        # --- Zone Points input ---
        self.zone_points_input = TextInput(
            hint_text="Enter zone points",
            multiline=True,
            size_hint=(None, None),
            size=(dp(200), dp(100)),
            pos_hint={"center_x": 0.5},
            background_normal='', background_active='',
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            font_size='18sp'
        )
        grid.add_widget(param_box("Zone Points:", self.zone_points_input, box_height=160))
            # --- Generate Coordinates button ---
        gen_btn = RoundedButton(
            text="Generate Coordinates",
            size_hint=(None, None),
            size=(dp(250), dp(50)),
            bg_color=(1, 1, 1, 1),
            font_size='18sp'
        )
        gen_btn.bind(on_release=self.generate_coordinates)

        # Center it properly
        btn_wrapper = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, None), height=dp(70))
        btn_wrapper.add_widget(gen_btn)
        grid.add_widget(btn_wrapper)

        # Add grid to top_layout
        top_layout.add_widget(grid)
        root.add_widget(top_layout)

        # --- BOTTOM BUTTONS ---
        bottom_layout = BoxLayout(orientation="vertical", spacing=40, padding=150, size_hint=(1, 0.15))

        save_btn = RoundedButton(
            text="Save",
            size_hint=(None, None),
            size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            bg_color=(0.0, 0.67, 0.93, 1),
            font_size='18sp'
        )
        save_btn.bind(on_release=self.save_data)

        back_btn = RoundedButton(
            text="Back",
            size_hint=(None, None),
            size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            bg_color=(1, 1, 1, 1),
            font_size='18sp'
        )
        back_btn.bind(on_release=lambda x: setattr(self.manager, "current", "login"))

        bottom_layout.add_widget(save_btn)
        bottom_layout.add_widget(back_btn)

        root.add_widget(bottom_layout)

        # Add everything to screen
        self.add_widget(root)
    

    def generate_coordinates(self, instance):
        try:
            zone_index = int(self.zone_spinner.text.split(" ")[-1])
            update_config_for_camera(zone_index)

            # Run co_ord.py and capture output
            result = subprocess.run(
                ["python3", "co_ord.py"], 
                capture_output=True, text=True
            )

            output = result.stdout.strip().splitlines()

            # Collect clicked points
            clicked_lines = [line for line in output if line.strip().startswith("- [")]
            if clicked_lines:
                coords = [eval(line.strip().replace("- ", "")) for line in clicked_lines]

                # ✅ Reflect in UI
                self.zone_points_input.text = "\n".join(str(p) for p in coords)

                # ✅ Also persist in config.yaml
                save_points_to_config(zone_index, coords)
            else:
                show_popup("No points clicked.")
        except Exception as e:
            show_popup(f"Error generating coords: {e}")
        

    def on_pre_enter(self):
        self.data = load_yaml_preserve()
        num_cam = self.data.get("serial", {}).get("num_cam", 4)

        # ✅ update zone spinner dynamically
        self.zone_spinner.values = [f"Camera {i}" for i in range(num_cam)]
        self.zone_spinner.text = "Camera 0"

        self.zone_points_input.text = self.get_zone_points_text(0)

    def on_zone_change(self, spinner, text):   # ✅ new method
        try:
            zone_index = int(text.split(" ")[-1])
            self.zone_points_input.text = self.get_zone_points_text(zone_index)
        except Exception:
            self.zone_points_input.text = ""

    def get_zone_points_text(self, zone_index):
        key = f"p{zone_index}_zone_coords"
        pts = self.data.get(key, {}).get("points", [])
        return "\n".join(str(p) for p in pts)

    def save_data(self, instance):
        try:
            zone_index = int(self.zone_spinner.text.split(" ")[-1])
            key = f"p{zone_index}_zone_coords"
            if key not in self.data:
                self.data[key] = {}
            if self.zone_points_input.text.strip():
                pts = [eval(line.strip()) for line in self.zone_points_input.text.strip().splitlines()]
                self.data[key]["points"] = format_points(pts)
            save_yaml_preserve(self.data)
            show_popup("User settings saved!")
        except Exception as e:
            show_popup(str(e))


# ---------------- APP ----------------
class ConfigApp(App):
    def build(self):
        Window.clearcolor = (0.68, 0.70, 0.68, 1)  # #ADB3AD
        Window.size = (800, 500)
        Window.resizable = False

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(AdminScreen(name="admin"))
        sm.add_widget(UserScreen(name="user"))
        return sm


if __name__ == "__main__":
    ConfigApp().run()
