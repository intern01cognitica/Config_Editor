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
from utils.logs import logger
from kivy.uix.screenmanager import ScreenManager, Screen
class UserScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = {}
        self.proc = None  # store the subprocess so we can kill it later
        self.current_zone_color = "red" 
        self.zone_color_map = {"Red": "red", "Orange": "orange", "Blue": "blue"}
        self.camera_labels = {
            "Camera 1": "Front Camera",
            "Camera 2": "Left Camera",
            "Camera 3": "Right Camera",
            "Camera 4": "Back Camera"
        }
        # Root layout
        root = BoxLayout(orientation="vertical")

        # --- TOP CONTENT (User Panel, Zone Selection, Zone Points) ---
        top_layout = BoxLayout(orientation="vertical", padding=150, spacing=60, size_hint=(1, 1.05))
        top_layout.add_widget(Label(text="User Panel", font_size=22, color=(0, 0, 0, 1)))

        # --- Grid for parameters (1 column) ---
        grid = GridLayout(cols=1, spacing=120, size_hint=(1, None))
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
        # self.zone_spinner = Spinner(
        #     text="Camera 1",
        #     values=[f"Camera {i}" for i in range(1,7)],
        #     size_hint=(None, None),
        #     size=(dp(200), dp(50)),
        #     pos_hint={"center_x": 0.5},
        #     option_cls=CustomLimitedSpinnerOption,
        #     background_normal='',
        #     background_color=(1, 1, 1, 1),
        #     color=(0, 0, 0, 1),
        #     font_size='18sp'
        # )
        # self.zone_spinner.dropdown_cls.max_height = dp(120)
        # self.zone_spinner.bind(text=self.on_camera_change)
        # grid.add_widget(param_box("Camera Selection:", self.zone_spinner))
        # dropdown_icon(self.zone_spinner)
        self.zone_spinner = Spinner(
            text="Front Camera",  # default
            values=list(self.camera_labels.values()),  # show only friendly names
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
        self.zone_spinner.bind(text=self.on_camera_change)
        grid.add_widget(param_box("Camera Selection:", self.zone_spinner))
        dropdown_icon(self.zone_spinner)


        self.zone_color_spinner = Spinner(
            text="Red",  # default visible
            values=list(self.zone_color_map.keys()),  # show pretty labels
            size_hint=(None, None), size=(dp(200), dp(50)),pos_hint={"center_x": 0.5},
            option_cls=CustomLimitedSpinnerOption,
            background_normal='', background_color=(1, 1, 1, 1),
            color=(0, 0, 0, 1), font_size='18sp'
        )
        self.zone_color_spinner.dropdown_cls.max_height = dp(120)
        self.zone_color_spinner.bind(text=self.on_zone_color_change)
        grid.add_widget(param_box("Zone Color:", self.zone_color_spinner))
        dropdown_icon(self.zone_color_spinner)


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
        btn_wrapper = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, None), height=dp(10))
        btn_wrapper.add_widget(gen_btn)
        grid.add_widget(btn_wrapper)

        # Add grid to top_layout
        top_layout.add_widget(grid)
        root.add_widget(top_layout)

        # --- BOTTOM BUTTONS ---
        bottom_layout = BoxLayout(orientation="vertical", spacing=20, padding=50, size_hint=(1, 0.15))

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
        # back_btn.bind(on_release=lambda x: setattr(self.manager, "current", "login"))
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
    def get_internal_camera_name(self, friendly_name):
        for internal, friendly in self.camera_labels.items():
            if friendly == friendly_name:
                return internal
        return friendly_name  # fallback

    # def generate_coordinates(self, instance):
    #     internal_name = self.get_internal_camera_name(self.zone_spinner.text)
    #     cam_index = int(internal_name.split(" ")[-1]) - 1


    #     zone_color = self.current_zone_color
    #     update_config_for_camera(cam_index)

    #     if self.proc and self.proc.poll() is None:
    #         if not hasattr(self, "running_popup") or self.running_popup is None:
    #             self.running_popup = show_popup("A camera process is already running.")
    #         return

    #     show_loading("Connecting to camera. Please Wait...")

    #     def task():
    #         try:
    #             self.proc = subprocess.Popen(
    #                 ["python3", "co_ord.py"],
    #                 stdout=subprocess.PIPE,
    #                 stderr=subprocess.PIPE,
    #                 text=True
    #             )
    #             time.sleep(0.2)

    #             # If process died immediately
    #             if self.proc.poll() is not None:
    #                 stdout, stderr = self.proc.communicate()
    #                 logger.error(f"Camera {cam_index+1} failed to start. stderr:\n{stderr}")
    #                 Clock.schedule_once(lambda dt: show_popup(f"Camera {cam_index+1} unreachable"))
    #                 return

    #             Clock.schedule_once(lambda dt: hide_loading())
    #             stdout, stderr = self.proc.communicate()

    #             # If process returned non-zero exit
    #             if self.proc.returncode != 0:
    #                 logger.error(
    #                     f"Camera {cam_index+1} process exited with code {self.proc.returncode}. stderr:\n{stderr}"
    #                 )
    #                 Clock.schedule_once(lambda dt: show_popup(f"Camera {cam_index+1} unreachable"))
    #                 return

    #             # Extract clicked coordinates
    #             clicked_lines = [
    #                 line for line in stdout.strip().splitlines()
    #                 if line.strip().startswith("- [")
    #             ]
    #             if clicked_lines:
    #                 coords = [eval(line.strip().replace("- ", "")) for line in clicked_lines]
    #                 Clock.schedule_once(lambda dt: setattr(
    #                     self.zone_points_input,
    #                     "text",
    #                     "\n".join(str(p) for p in coords)
    #                 ))
    #                 save_points_to_config(cam_index, zone_color, coords)
    #                 Clock.schedule_once(lambda dt: show_popup(
    #                     f"{zone_color.title()} zone updated for Camera {cam_index+1}"
    #                 ))
    #             else:
    #                 Clock.schedule_once(lambda dt: show_popup(f"No points clicked for Camera {cam_index+1}"))

    #         except Exception:
    #             logger.exception(f"Unexpected error in generate_coordinates for Camera {cam_index+1}")
    #             Clock.schedule_once(lambda dt: show_popup(f"Camera {cam_index+1} unreachable"))

    #         finally:
    #             if hasattr(self, "running_popup") and self.running_popup:
    #                 try:
    #                     self.running_popup.dismiss()
    #                 except Exception:
    #                     pass
    #                 self.running_popup = None
    #             if self.proc and self.proc.poll() is None:
    #                 try:
    #                     self.proc.terminate()
    #                 except Exception:
    #                     pass
    #             self.proc = None

    #     threading.Thread(target=task, daemon=True).start()
    def generate_coordinates(self, instance):
        internal_name = self.get_internal_camera_name(self.zone_spinner.text)
        cam_index = int(internal_name.split(" ")[-1]) - 1
        friendly_name = self.zone_spinner.text  # already shows Front/Left/Right/Back

        zone_color = self.current_zone_color
        update_config_for_camera(cam_index)

        if self.proc and self.proc.poll() is None:
            if not hasattr(self, "running_popup") or self.running_popup is None:
                self.running_popup = show_popup("A camera process is already running.")
            return

        show_loading(f"Connecting to {friendly_name}. Please Wait...")

        def task():
            try:
                self.proc = subprocess.Popen(
                    ["python3", "co_ord.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                time.sleep(0.2)

                # If process died immediately
                if self.proc.poll() is not None:
                    stdout, stderr = self.proc.communicate()
                    logger.error(f"{friendly_name} failed to start. stderr:\n{stderr}")
                    Clock.schedule_once(lambda dt: show_popup(f"{friendly_name} unreachable"))
                    return

                Clock.schedule_once(lambda dt: hide_loading())
                stdout, stderr = self.proc.communicate()

                # If process returned non-zero exit
                if self.proc.returncode != 0:
                    logger.error(f"{friendly_name} process exited with code {self.proc.returncode}. stderr:\n{stderr}")
                    Clock.schedule_once(lambda dt: show_popup(f"{friendly_name} unreachable"))
                    return

                # Extract clicked coordinates
                clicked_lines = [
                    line for line in stdout.strip().splitlines()
                    if line.strip().startswith("- [")
                ]
                if clicked_lines:
                    coords = [eval(line.strip().replace("- ", "")) for line in clicked_lines]
                    Clock.schedule_once(lambda dt: setattr(
                        self.zone_points_input,
                        "text",
                        "\n".join(str(p) for p in coords)
                    ))
                    save_points_to_config(cam_index, zone_color, coords)
                else:
                    Clock.schedule_once(lambda dt: show_popup(f"No points clicked for {friendly_name}"))

            except Exception:
                logger.exception(f"Unexpected error in generate_coordinates for {friendly_name}")
                Clock.schedule_once(lambda dt: show_popup(f"{friendly_name} unreachable"))

            finally:
                if hasattr(self, "running_popup") and self.running_popup:
                    try:
                        self.running_popup.dismiss()
                    except Exception:
                        pass
                    self.running_popup = None
                if self.proc and self.proc.poll() is None:
                    try:
                        self.proc.terminate()
                    except Exception:
                        pass
                self.proc = None

        threading.Thread(target=task, daemon=True).start()

            
    # def on_pre_enter(self):
    #     sync_zones_from_conc_to_config()
    #     self.data = load_yaml_preserve()
    #     num_cam = self.data.get("serial", {}).get("num_cam", 4)

    #     # ✅ update zone spinner dynamically
    #     self.zone_spinner.values = [f"Camera {i+1}" for i in range(num_cam)]
    #     self.zone_spinner.text = "Camera 1"
    def on_pre_enter(self):
        sync_zones_from_conc_to_config()
        self.data = load_yaml_preserve()
        num_cam = self.data.get("serial", {}).get("num_cam", 4)

        # ✅ use friendly names instead of "Camera X"
        self.zone_spinner.values = list(self.camera_labels.values())[:num_cam]
        self.zone_spinner.text = self.camera_labels["Camera 1"]  # default = Front Camera

        # set points for first camera (index 0)
        self.zone_points_input.text = self.get_zone_points_text(0, self.current_zone_color)


        self.zone_points_input.text = self.get_zone_points_text(0,self.current_zone_color)
    def on_camera_change(self, spinner, text):
        internal_name = self.get_internal_camera_name(self.zone_spinner.text)
        cam_index = int(internal_name.split(" ")[-1]) - 1
        sync_zones_from_conc_to_config()
        self.data = load_yaml_preserve()
        self.zone_points_input.text = self.get_zone_points_text(cam_index, self.current_zone_color)
    def on_zone_color_change(self, spinner, text):
        """Handle zone color selection change."""
        # Map pretty label -> internal lowercase
        self.current_zone_color = self.zone_color_map[text]
        internal_name = self.get_internal_camera_name(self.zone_spinner.text)
        cam_index = int(internal_name.split(" ")[-1]) - 1
        sync_zones_from_conc_to_config()
        self.data = load_yaml_preserve()
        self.zone_points_input.text = self.get_zone_points_text(cam_index, self.current_zone_color)

    def get_zone_points_text(self, cam_index, zone_color):
        key = f"p{cam_index}_zone_coords"
        pts = self.data.get(key, {}).get(zone_color, [])
        return "\n".join(str(p) for p in pts)

    # def save_data(self, instance):
    #     try:
    #         zone_index = int(self.zone_spinner.text.split(" ")[-1]) - 1
    #         if self.zone_points_input.text.strip():
    #             pts = [eval(line.strip()) for line in self.zone_points_input.text.strip().splitlines()]
    #             save_points_to_config(zone_index, self.current_zone_color, pts)
    #             save_points_to_conc(zone_index, self.current_zone_color, pts)
    #             show_popup(f"User settings saved for Camera {zone_index+1}")
    #         else:
    #             show_popup("No points entered")
    #     except Exception as e:
    #         show_popup(str(e))
    def save_data(self, instance):
        try:
            internal_name = self.get_internal_camera_name(self.zone_spinner.text)
            zone_index = int(internal_name.split(" ")[-1]) - 1
            friendly_name = self.zone_spinner.text
            zone_color = self.current_zone_color

            raw_text = self.zone_points_input.text.strip()

            if not raw_text:
                show_popup("No points entered")
                return

            pts = []
            for line in raw_text.splitlines():
                try:
                    val = eval(line.strip(), {}, {})  # safe eval: no globals/locals
                    if (
                        isinstance(val, (list, tuple)) and
                        len(val) == 2 and
                        all(isinstance(x, (int, float)) for x in val)
                    ):
                        pts.append([int(val[0]), int(val[1])])
                    else:
                        raise ValueError
                except Exception:
                    show_popup(f"Invalid point format: {line}\nExpected like: [100, 200]")
                    return  # stop on first invalid entry

            # ✅ If we get here, all points are valid
            save_points_to_config(zone_index, self.current_zone_color, pts)
            save_points_to_conc(zone_index, self.current_zone_color, pts)
            # show_popup(f"User settings saved for Camera {zone_index+1}")
            show_popup(f"{zone_color.title()} zone updated for {friendly_name}")

        except Exception as e:
            show_popup(f"Error: {e}")

