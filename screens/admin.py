from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.widget import Widget
from utils.ui_helpers import show_popup,RoundedButton,CustomLimitedSpinnerOption,dropdown_icon
from utils.yaml_utils import load_yaml_preserve,update_yaml_value,update_yaml_list,update_yaml
from kivy.uix.screenmanager import ScreenManager, Screen
class AdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {}
        self.camera_labels = {
            "Camera 1": "Front Camera",
            "Camera 2": "Left Camera",
            "Camera 3": "Right Camera",
            "Camera 4": "Back Camera"
        }

        # Root layout
        root = BoxLayout(orientation="vertical")

        # # --- TOP CONTENT (Admin Panel, Params, Threshold) ---
        # top_layout = BoxLayout(orientation="vertical", padding=350, spacing=10, size_hint=(1, 3.95))
        top_layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(100), size_hint=(1, 0.55))
        top_layout.add_widget(Label(text="Admin Panel", font_size=22, color=(0, 0, 0, 1)))

        # --- Grid for parameters ---
        # grid = GridLayout(cols=2, spacing=100, size_hint=(1, None))
        grid = GridLayout(cols=2, spacing=dp(120), padding=[dp(100), dp(20)], size_hint=(1, None))
        grid.bind(minimum_height=grid.setter("height"))

        def param_box(label_text, widget):
            box = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(60), spacing=20)
            lbl = Label(
                text=label_text,
                color=(0, 0, 0, 1),
                size_hint=(0.4, None),   # take 40% of the row
                height=dp(50),
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
            text="", values=["1", "2","3","4"],
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            option_cls=CustomLimitedSpinnerOption
        )
        self.num_cam_spinner.dropdown_cls.max_height = dp(120)
        grid.add_widget(param_box("Number of Cameras:", self.num_cam_spinner))
        dropdown_icon(self.num_cam_spinner)

 

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
        dropdown_icon(self.failsafe_spinner) 


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
        dropdown_icon(self.interlock_spinner) 

         # Show Confidence
        self.show_conf_spinner = Spinner(
            text="Disable", values=["Enable", "Disable"],
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        grid.add_widget(param_box("Show Confidence:", self.show_conf_spinner))
        dropdown_icon(self.show_conf_spinner) 

        # Camera Selection
        # self.camera_spinner = Spinner(
        #     text="Camera 1", values=[f"Camera {i+1}" for i in range(6)],
        #     background_normal='', background_color=(1, 1, 1, 1),
        #     color=(0, 0, 0, 1), font_size='18sp',
        #     size_hint=(None, None), size=(dp(200), dp(50)),
        #     pos_hint={"center_x": 0.5},
        #     option_cls=CustomLimitedSpinnerOption
        # )
        self.camera_spinner = Spinner(
            text="Front Camera", values=list(self.camera_labels.values()),
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        self.camera_spinner.dropdown_cls.max_height = dp(120)

        self.camera_spinner.bind(text=self.on_camera_change)
        grid.add_widget(param_box("Camera Selection:", self.camera_spinner))
        dropdown_icon(self.camera_spinner) 

        # # Add top section to root
        self.threshold_input = TextInput(
            multiline=False,
            size_hint=(None, None),
            size=(dp(200), dp(50)),
            halign="center",
            background_normal='', background_active='',
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            font_size='18sp'
        )
        self.threshold_input.bind(size=lambda inst, val: setattr(inst, "text_size", inst.size))
        self.threshold_input.bind(text=self.enforce_threshold_input) 
        grid.add_widget(param_box("Threshold:", self.threshold_input))
        # Dropbox Upload
        self.dropbox_spinner = Spinner(
            text="Disable", values=["Enable", "Disable"],
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        grid.add_widget(param_box("Cloud App:", self.dropbox_spinner))
        dropdown_icon(self.dropbox_spinner)

        # Encryption
        self.encryption_spinner = Spinner(
            text="Disable", values=["Enable", "Disable"],
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp',
            size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption
        )
        grid.add_widget(param_box("Encryption:", self.encryption_spinner))
        dropdown_icon(self.encryption_spinner)

       # --- Facial centered below ---
        facial_anchor = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 0.75), height=dp(200), padding=(0, dp(50), 0, 0))
        facial_box = BoxLayout(orientation="horizontal", spacing=5, size_hint=(None, None))
        facial_box.size = (dp(300), dp(40))

        facial_box.add_widget(Label(
            text="Facial:", 
            color=(0, 0, 0, 1), 
            size_hint=(None, None), 
            size=(dp(100), dp(40)),
            font_size='18sp',
        ))

        self.facial_spinner = Spinner(
            text="Disable", values=["Enable", "Disable"],
            size_hint=(None, None),
            size=(dp(150), dp(40)),
            halign="center",
            background_normal='',
            background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), 
            font_size='18sp',
            option_cls=CustomLimitedSpinnerOption
        )
        self.facial_spinner.bind(size=lambda inst, val: setattr(inst, "text_size", inst.size))
        dropdown_icon(self.facial_spinner) 

        facial_box.add_widget(self.facial_spinner)   # ✅ use new spinner here
        facial_anchor.add_widget(facial_box) 
        top_layout.add_widget(grid)

        top_layout.add_widget(facial_anchor)

        # top_layout.add_widget(grid)

        root.add_widget(top_layout)

        # --- BOTTOM BUTTONS ---
        bottom_layout = BoxLayout(orientation="vertical", spacing=10, padding=20, size_hint=(1, 0.15))

        save_btn = RoundedButton(
            text="Save", size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5}, bg_color=(0.0, 0.67, 0.93, 1),font_size='18sp'
        )
        save_btn.bind(on_release=self.save_data)

        logout_btn = RoundedButton(
            text="Logout", size_hint=(None, None), size=(dp(200), dp(50)),
            pos_hint={"center_x": 0.5}, bg_color=(1, 1, 1, 1),font_size='18sp'
        )
        # logout_btn.bind(on_release=lambda x: setattr(self.manager, "current", "login"))
        logout_btn.bind(on_release=lambda x: self.logout())

        bottom_layout.add_widget(save_btn)
        bottom_layout.add_widget(logout_btn)

        # Add bottom section to root
        root.add_widget(bottom_layout)

        # Add everything to screen
        self.add_widget(root)
    def logout(self):
        self.manager.current = "login"
        # First unmaximize, then shrink
        Window.restore()  
        Window.size = (800, 500)
    def get_internal_camera_name(self, friendly_name):
        for internal, friendly in self.camera_labels.items():
            if friendly == friendly_name:
                return internal
        return friendly_name  # fallback

    def on_camera_change(self, spinner, text):
        """Update threshold when user selects a different camera."""
        try:
            # cam_index = int(text.split(" ")[-1])-1
            internal_name = self.get_internal_camera_name(self.camera_spinner.text)
            cam_index = int(internal_name.split(" ")[-1]) - 1
            key = f"background_p{cam_index}"
            self.threshold_input.text = str(self.data.get(key, {}).get("threshold", ""))
        except Exception:
            self.threshold_input.text = ""
    def validate_threshold(self, value: str):
        try:
            num = float(value)
            if 0.0 <= num <= 1.0:
                return round(num, 2)
            return None
            # return round(num, 2)  # always 2 decimals
        except ValueError:
            return None

    def enforce_threshold_input(self, instance, value):
        import re
        if not re.match(r'^\d*\.?\d{0,2}$', value):
            show_popup("Threshold must be number less than or equal to 1")
            # cleanup input live
            parts = re.sub(r'[^0-9.]', '', value).split('.')
            if len(parts) > 2:
                instance.text = parts[0] + '.' + ''.join(parts[1:])
            else:
                instance.text = '.'.join(parts[:2])

    def load_data(self):
        self.data = load_yaml_preserve()
        self.failsafe_spinner.text = "Enable" if self.data.get("serial", {}).get("enable_Failsafe", 0) == 1 else "Disable"
        self.interlock_spinner.text = "Enable" if self.data.get("serial", {}).get("enable_brake", 0) == 1 else "Disable"
        # ✅ Show Confidence
        show_conf = self.data.get("model", {}).get("show_confidence", False)
        self.show_conf_spinner.text = "Enable" if show_conf else "Disable"

        # ✅ Fetch num_cam from YAML (default 4 if missing)
        num_cam = str(self.data.get("model", {}).get("num_cam", 4))
        if num_cam not in ["1", "2","3","4"]:  
            num_cam = "4"
        self.num_cam_spinner.text = num_cam

        # # ✅ Update camera spinner dynamically
        # self.camera_spinner.values = [f"Camera {i+1}" for i in range(int(num_cam))]
        # self.camera_spinner.text = "Camera 1"

        # self.threshold_input.text = str(self.data.get("background_p0", {}).get("threshold", ""))
        available_cameras = [self.camera_labels[f"Camera {i+1}"]
                         for i in range(int(num_cam))
                         if f"Camera {i+1}" in self.camera_labels]

        self.camera_spinner.values = available_cameras
        self.camera_spinner.text = available_cameras[0]

        # Threshold for first camera
        internal_name = self.get_internal_camera_name(self.camera_spinner.text)
        cam_index = int(internal_name.split(" ")[-1]) - 1
        self.threshold_input.text = str(self.data.get(f"background_p{cam_index}", {}).get("threshold", ""))
        # ✅ Load cloud_dashboard values
        cloud = self.data.get("cloud_dashboard", {})
        self.dropbox_spinner.text = "Enable" if cloud.get("dropbox_upload", False) else "Disable"
        self.encryption_spinner.text = "Enable" if cloud.get("encryption", False) else "Disable"
        self.facial_spinner.text = "Enable" if self.data.get("serial", {}).get("enable_Facial", 0) == 1 else "Disable"



   
    def save_data(self, instance):
        try:
            internal_name = self.get_internal_camera_name(self.camera_spinner.text)
            # cam_index = int(self.camera_spinner.text.split(" ")[-1]) - 1
            cam_index = int(internal_name.split(" ")[-1]) - 1
            friendly_name = self.camera_spinner.text
            key = f"background_p{cam_index}"

            # --- Load current values ---
            data = load_yaml_preserve()

            prev_num_cam = data.get("model", {}).get("num_cam")
            prev_failsafe = data.get("serial", {}).get("enable_Failsafe")
            prev_interlock = data.get("serial", {}).get("enable_brake")
            prev_threshold = data.get(key, {}).get("threshold")
            prev_conf = data.get("model", {}).get("show_confidence")
            prev_dropbox = data.get("cloud_dashboard", {}).get("dropbox_upload")
            prev_encryption = data.get("cloud_dashboard", {}).get("encryption")
            prev_facial = data.get("serial", {}).get("enable_Facial")

            # --- New values from UI ---
            new_num_cam = int(self.num_cam_spinner.text)
            new_failsafe = 1 if self.failsafe_spinner.text == "Enable" else 0
            new_interlock = 1 if self.interlock_spinner.text == "Enable" else 0
            # new_threshold = float(self.threshold_input.text.strip())
            # --- New values from UI ---
            new_conf = True if self.show_conf_spinner.text == "Enable" else False
            new_dropbox = True if self.dropbox_spinner.text == "Enable" else False
            new_encryption = True if self.encryption_spinner.text == "Enable" else False
            new_Facial = 1 if self.facial_spinner.text == "Enable" else 0
            

            raw_threshold = self.threshold_input.text.strip()
            validated = self.validate_threshold(raw_threshold)

            if validated is None:
                show_popup("Threshold must be number less than or equal to 1")
                return

            # ✅ overwrite with safe format
            self.threshold_input.text = f"{validated:.2f}"
            new_threshold = validated
            # --- Collect messages ---
            messages = []

            if prev_num_cam != new_num_cam:
                update_yaml_value("model.num_cam", new_num_cam)
                messages.append(f"Number of cameras updated to {new_num_cam}")
            
            if prev_failsafe != new_failsafe:
                update_yaml_value("serial.enable_Failsafe", new_failsafe)
                messages.append(f"Failsafe set to {self.failsafe_spinner.text}")

            if prev_interlock != new_interlock:
                update_yaml_value("serial.enable_brake", new_interlock)
                messages.append(f"Interlock set to {self.interlock_spinner.text}")

            if prev_threshold != new_threshold:
                update_yaml_value(f"{key}.threshold", new_threshold)
                messages.append(f"Threshold updated for  {friendly_name}")
            if prev_conf != new_conf:
                update_yaml_value("model.show_confidence", str(new_conf))
                messages.append(f"Show Confidence set to {self.show_conf_spinner.text}")
            if new_dropbox and not new_encryption:
                new_encryption = True
                self.encryption_spinner.text = "Enable"  # update UI as well
                messages.append("Cloud App requires Encryption is set to be True ")

            if prev_dropbox != new_dropbox:
                update_yaml_value("cloud_dashboard.dropbox_upload", new_dropbox)
                messages.append(f"Cloup App  set to {self.dropbox_spinner.text}")

            if prev_encryption != new_encryption:
                update_yaml_value("cloud_dashboard.encryption", new_encryption)
                messages.append(f"Encryption set to {self.encryption_spinner.text}")
            if prev_facial != new_Facial:
                update_yaml_value("serial.enable_Facial", new_Facial)
                messages.append(f"Facial set to {self.facial_spinner.text}")
            # --- Final popup ---
            if not messages:
                messages.append("No changes detected — settings re-saved.")
            self.data = load_yaml_preserve()

            show_popup("\n".join(messages))

        except Exception as e:
            show_popup(f"Error: {str(e)}")
