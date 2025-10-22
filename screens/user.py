import threading
import time
from kivy.clock import Clock
import subprocess
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.widget import Widget
from utils.ui_helpers import show_popup,RoundedButton,CustomLimitedSpinnerOption,show_loading,hide_loading,dropdown_icon
from utils.yaml_utils import update_config_for_camera,save_points_to_config,load_yaml_preserve,format_points,update_yaml_list,update_yaml_value,update_yaml,sync_zones_from_conc_to_config,save_points_to_conc
from kivy.uix.screenmanager import ScreenManager, Screen
class UserScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {}
        self.proc = None  # store the subprocess so we can kill it later

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
            text="Camera 1",
            values=[f"Camera {i}" for i in range(1,7)],
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
        dropdown_icon(self.zone_spinner)


        # --- Zone Points input ---
        self.zone_points_input = TextInput(
            hint_text="Enter zone points",
            multiline=True,
            size_hint=(None, None),
            size=(dp(200), dp(120)),
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
        back_btn.bind(on_release=lambda x: self.go_back())

        bottom_layout.add_widget(save_btn)
        bottom_layout.add_widget(back_btn)

        root.add_widget(bottom_layout)

        # Add everything to screen
        self.add_widget(root)
    def go_back(self):
        self.manager.current = "login"
        Window.restore()          # unmaximize first
        Window.size = (800, 500)
  
    def generate_coordinates(self, instance):
        zone_index = int(self.zone_spinner.text.split(" ")[-1]) - 1
        update_config_for_camera(zone_index)

        # 🚩 Block if already running
        if self.proc and self.proc.poll() is None:
            # keep reference to popup so we can dismiss later
            if not hasattr(self, "running_popup") or self.running_popup is None:
                self.running_popup = show_popup("A camera process is already running. Please close it before starting another.")
            return

        # Show loading immediately
        show_loading("Connecting to camera. Please Wait...")

        def task():
            try:
                self.proc = subprocess.Popen(
                    ["python3", "co_ord.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Poll the process until it either fails or is running fine
                time.sleep(2)  # tiny grace period
                if self.proc.poll() is not None:
                    # 🚩 process already exited = unreachable
                    Clock.schedule_once(lambda dt: hide_loading())
                    Clock.schedule_once(lambda dt: show_popup(f"Camera {zone_index+1} unreachable"))
                    return

                # 🚩 If feed is alive → hide loading
                Clock.schedule_once(lambda dt: hide_loading())

                # Wait until feed closes (ESC/←/→)
                stdout, stderr = self.proc.communicate()

                # After feed ends, check return code
                if self.proc.returncode != 0:
                    Clock.schedule_once(lambda dt: show_popup(f"Camera {zone_index+1} unreachable"))
                    return

                # Handle clicked points
                output = stdout.strip().splitlines()
                clicked_lines = [line for line in output if line.strip().startswith("- [")]

                if clicked_lines:
                    coords = [eval(line.strip().replace("- ", "")) for line in clicked_lines]
                    Clock.schedule_once(lambda dt: setattr(
                        self.zone_points_input, "text",
                        "\n".join(str(p) for p in coords)
                    ))
                    save_points_to_config(zone_index, coords)
                    Clock.schedule_once(lambda dt: show_popup(f"Zone points updated for Camera {zone_index+1}"))
                else:
                    Clock.schedule_once(lambda dt: show_popup(f"No points clicked for Camera {zone_index+1}"))

            except Exception as e:
                Clock.schedule_once(lambda dt, err=e: show_popup(f"Error generating coords: {err}"))

            finally:
                # 🚩 Close "already running" popup if it was open
                if hasattr(self, "running_popup") and self.running_popup:
                    try:
                        self.running_popup.dismiss()
                    except Exception:
                        pass
                    self.running_popup = None

                # 🚩 Kill process if still alive
                if self.proc and self.proc.poll() is None:
                    try:
                        self.proc.terminate()
                    except Exception:
                        pass
                self.proc = None

        threading.Thread(target=task, daemon=True).start()

            
    def on_pre_enter(self):
        sync_zones_from_conc_to_config()
        self.data = load_yaml_preserve()
        num_cam = self.data.get("serial", {}).get("num_cam", 4)

        # ✅ update zone spinner dynamically
        self.zone_spinner.values = [f"Camera {i+1}" for i in range(num_cam)]
        self.zone_spinner.text = "Camera 1"

        self.zone_points_input.text = self.get_zone_points_text(0)

    def on_zone_change(self, spinner, text):   # ✅ new method
        try:
            zone_index = int(text.split(" ")[-1])-1
            self.zone_points_input.text = self.get_zone_points_text(zone_index)
        except Exception:
            self.zone_points_input.text = ""

    def get_zone_points_text(self, zone_index):
        key = f"p{zone_index}_zone_coords"
        pts = self.data.get(key, {}).get("points", [])
        return "\n".join(str(p) for p in pts)

    def save_data(self, instance):
        try:
            zone_index = int(self.zone_spinner.text.split(" ")[-1]) - 1
            if self.zone_points_input.text.strip():
                pts = [eval(line.strip()) for line in self.zone_points_input.text.strip().splitlines()]
                save_points_to_config(zone_index, pts)  # ✅ config.yaml
                save_points_to_conc(zone_index, pts)
                show_popup(f"User settings saved for Camera {zone_index+1}")
            else:
                show_popup("No points entered")
        except Exception as e:
            show_popup(str(e))
