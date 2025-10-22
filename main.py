from utils import logs
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from utils.yaml_utils import  sync_zones_from_conc_to_config
from screens.login import LoginScreen
from screens.admin import AdminScreen
from screens.user  import UserScreen

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
        sm.bind(current=self.on_screen_change)
        Window.bind(on_request_close=self.on_close)
        Window.bind(on_keyboard=self.on_keyboard) 
        return sm
    def on_screen_change(self, sm, screen_name):
        """Adjust window size depending on active screen."""
        if screen_name == "login":
            Window.size = (800, 500)
        else:  # admin or user
            Window.maximize()

    def on_keyboard(self, window, key, scancode, codepoint, modifiers):
        if key == 27:  # Esc key
            return True  # 👈 prevent closing the app
        return False
    def on_close(self, *args, **kwargs):
        """Kill subprocess if still running before app closes"""
        try:
            sm = self.root
            if sm.has_screen("user"):
                user_screen = sm.get_screen("user")
                if hasattr(user_screen, "proc") and user_screen.proc:
                    if user_screen.proc.poll() is None:  # still running
                        user_screen.proc.terminate()
                        try:
                            user_screen.proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            user_screen.proc.kill()
        except Exception as e:
            print(f"Error during on_close: {e}")
        return False  # allow app to close



if __name__ == "__main__":
    sync_zones_from_conc_to_config("config.yaml", "conc.yaml")
    ConfigApp().run()
