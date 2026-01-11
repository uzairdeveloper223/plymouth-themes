#!/usr/bin/env python3

## Plymouth Toolkit - Preview, Apply etc
## Author : Uzair Mughal (uzairdeveloper223)
## Mail : contact@uzair.is-a.dev
## Instagram: @mughal_x22
## Discord: @mughal_x22

import os
import sys
import subprocess
from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GdkPixbuf, GLib, Gdk
except ImportError:
    print("Error: GTK3 is required. Install with:")
    print("  Ubuntu/Debian: sudo apt install python3-gi gir1.2-gtk-3.0")
    print("  Fedora: sudo dnf install python3-gobject gtk3")
    print("  Arch: sudo pacman -S python-gobject gtk3")
    sys.exit(1)


class PlymouthViewer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Plymouth Theme Viewer")
        self.set_default_size(900, 700)
        self.set_border_width(10)
        self.base_dir = Path(__file__).parent.resolve()
        self.current_frames = []
        self.current_frame_index = 0
        self.animation_timeout_id = None
        self.animation_speed = 50
        self.themes = self.discover_themes()
        self.setup_ui()
        self.connect("destroy", self.on_quit)

    def discover_themes(self):
        themes = {}
        pack_dirs = sorted(self.base_dir.glob("pack_*"))
        for pack_dir in pack_dirs:
            pack_name = pack_dir.name
            themes[pack_name] = []
            for theme_dir in sorted(pack_dir.iterdir()):
                if theme_dir.is_dir():
                    plymouth_files = list(theme_dir.glob("*.plymouth"))
                    if plymouth_files:
                        theme_name = theme_dir.name
                        frames = sorted(theme_dir.glob("progress-*.png"))
                        themes[pack_name].append({
                            'name': theme_name,
                            'path': theme_dir,
                            'frame_count': len(frames),
                            'plymouth_file': plymouth_files[0]
                        })
        return themes

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add(main_box)
        left_panel = self.create_theme_list_panel()
        main_box.pack_start(left_panel, False, False, 0)
        right_panel = self.create_preview_panel()
        main_box.pack_start(right_panel, True, True, 0)

    def create_theme_list_panel(self):
        frame = Gtk.Frame(label="Themes")
        frame.set_size_request(250, -1)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        frame.add(scrolled)
        self.theme_store = Gtk.TreeStore(str, str, str)
        for pack_name, pack_themes in self.themes.items():
            pack_display = pack_name.replace("_", " ").title()
            pack_iter = self.theme_store.append(None, [f"📁 {pack_display} ({len(pack_themes)})", "", pack_name])
            for theme in pack_themes:
                display_name = theme['name'].replace("_", " ").title()
                self.theme_store.append(pack_iter, [f"  🎨 {display_name}", str(theme['path']), ""])
        self.theme_tree = Gtk.TreeView(model=self.theme_store)
        self.theme_tree.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Theme", renderer, text=0)
        self.theme_tree.append_column(column)
        self.theme_tree.connect("row-activated", self.on_theme_selected)
        self.theme_tree.expand_all()
        scrolled.add(self.theme_tree)
        return frame

    def create_preview_panel(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        preview_frame = Gtk.Frame(label="Preview")
        preview_event_box = Gtk.EventBox()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"eventbox { background-color: #000000; }")
        preview_event_box.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.preview_area = Gtk.Image()
        self.preview_area.set_size_request(640, 400)
        preview_event_box.add(self.preview_area)
        preview_frame.add(preview_event_box)
        vbox.pack_start(preview_frame, True, True, 0)
        self.info_label = Gtk.Label(label="Select a theme to preview")
        self.info_label.set_line_wrap(True)
        vbox.pack_start(self.info_label, False, False, 0)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        controls_box.set_halign(Gtk.Align.CENTER)
        self.play_button = Gtk.Button(label="▶ Play")
        self.play_button.connect("clicked", self.on_play_clicked)
        self.play_button.set_sensitive(False)
        controls_box.pack_start(self.play_button, False, False, 0)
        self.stop_button = Gtk.Button(label="⏹ Stop")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_sensitive(False)
        controls_box.pack_start(self.stop_button, False, False, 0)
        speed_label = Gtk.Label(label="Speed:")
        controls_box.pack_start(speed_label, False, False, 10)
        self.speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 200, 10)
        self.speed_scale.set_value(50)
        self.speed_scale.set_size_request(150, -1)
        self.speed_scale.set_inverted(True)
        self.speed_scale.connect("value-changed", self.on_speed_changed)
        controls_box.pack_start(self.speed_scale, False, False, 0)
        vbox.pack_start(controls_box, False, False, 0)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.CENTER)
        self.preview_plymouth_btn = Gtk.Button(label="🖥 Preview with Plymouth")
        self.preview_plymouth_btn.connect("clicked", self.on_preview_plymouth)
        self.preview_plymouth_btn.set_sensitive(False)
        self.preview_plymouth_btn.set_tooltip_text("Preview using plymouth-x11 (requires root)")
        action_box.pack_start(self.preview_plymouth_btn, False, False, 0)
        self.install_button = Gtk.Button(label="📦 Install Theme")
        self.install_button.connect("clicked", self.on_install_clicked)
        self.install_button.set_sensitive(False)
        self.install_button.set_tooltip_text("Copy theme to /usr/share/plymouth/themes/")
        action_box.pack_start(self.install_button, False, False, 0)
        self.apply_button = Gtk.Button(label="✓ Apply Theme")
        self.apply_button.connect("clicked", self.on_apply_clicked)
        self.apply_button.set_sensitive(False)
        self.apply_button.set_tooltip_text("Set as default Plymouth theme (requires root)")
        action_box.pack_start(self.apply_button, False, False, 0)
        vbox.pack_start(action_box, False, False, 10)
        return vbox

    def on_theme_selected(self, tree_view, path, column):
        model = tree_view.get_model()
        iter = model.get_iter(path)
        theme_path = model.get_value(iter, 1)
        if not theme_path:
            return
        self.load_theme(Path(theme_path))

    def load_theme(self, theme_path):
        self.stop_animation()
        self.current_theme_path = theme_path
        self.current_frames = []
        self.current_frame_index = 0
        frame_files = list(theme_path.glob("progress-*.png"))
        def extract_number(path):
            try:
                return int(path.stem.split("-")[1])
            except (IndexError, ValueError):
                return 0
        frame_files = sorted(frame_files, key=extract_number)
        if not frame_files:
            frame_files = sorted(theme_path.glob("*.png"))
            frame_files = [f for f in frame_files if any(c.isdigit() for c in f.stem)]
        if not frame_files:
            self.info_label.set_text(f"No animation frames found in {theme_path.name}")
            return
        for frame_file in frame_files:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(frame_file))
                scaled = self.scale_pixbuf(pixbuf, 640, 400)
                self.current_frames.append(scaled)
            except Exception as e:
                print(f"Error loading {frame_file}: {e}")
        if self.current_frames:
            self.preview_area.set_from_pixbuf(self.current_frames[0])
            theme_name = theme_path.name.replace("_", " ").title()
            self.info_label.set_text(f"Theme: {theme_name}\nFrames: {len(self.current_frames)}\nPath: {theme_path}")
            self.play_button.set_sensitive(True)
            self.stop_button.set_sensitive(True)
            self.preview_plymouth_btn.set_sensitive(True)
            self.install_button.set_sensitive(True)
            self.apply_button.set_sensitive(True)
            self.start_animation()

    def scale_pixbuf(self, pixbuf, max_width, max_height):
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        scale_w = max_width / width
        scale_h = max_height / height
        scale = min(scale_w, scale_h, 1.0)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

    def start_animation(self):
        if not self.current_frames:
            return
        if self.animation_timeout_id:
            GLib.source_remove(self.animation_timeout_id)
            self.animation_timeout_id = None
        self.current_frame_index = 0
        self.animation_timeout_id = GLib.timeout_add(self.animation_speed, self.animate_frame)
        self.play_button.set_label("⏸ Pause")

    def stop_animation(self):
        if self.animation_timeout_id is not None:
            try:
                GLib.source_remove(self.animation_timeout_id)
            except:
                pass
            self.animation_timeout_id = None
        self.current_frame_index = 0
        self.play_button.set_label("▶ Play")

    def animate_frame(self):
        if not self.current_frames:
            self.animation_timeout_id = None
            return False
        if self.current_frame_index >= len(self.current_frames):
            self.current_frame_index = 0
        self.preview_area.set_from_pixbuf(self.current_frames[self.current_frame_index])
        self.current_frame_index = (self.current_frame_index + 1) % len(self.current_frames)
        return True

    def on_play_clicked(self, button):
        if self.animation_timeout_id:
            self.stop_animation()
        else:
            self.start_animation()

    def on_stop_clicked(self, button):
        self.stop_animation()
        self.current_frame_index = 0
        if self.current_frames and len(self.current_frames) > 0:
            self.preview_area.set_from_pixbuf(self.current_frames[0])

    def on_speed_changed(self, scale):
        self.animation_speed = int(scale.get_value())
        if self.animation_timeout_id:
            self.stop_animation()
            self.start_animation()

    def on_preview_plymouth(self, button):
        if not hasattr(self, 'current_theme_path'):
            return
        theme_name = self.current_theme_path.name
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Preview with Plymouth"
        )
        dialog.format_secondary_text(
            f"This will temporarily install and preview '{theme_name}' using plymouth-x11.\n\n"
            "Requires root privileges and plymouth-x11 package.\n\n"
            "Run this command in terminal:\n"
            f"sudo cp -r {self.current_theme_path} /usr/share/plymouth/themes/ && "
            f"sudo plymouth-set-default-theme {theme_name} && "
            f"sudo {self.base_dir}/showplymouth.sh 10"
        )
        dialog.run()
        dialog.destroy()

    def on_install_clicked(self, button):
        if not hasattr(self, 'current_theme_path'):
            return
        theme_name = self.current_theme_path.name
        dest_path = f"/usr/share/plymouth/themes/{theme_name}"
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Install '{theme_name}'?"
        )
        dialog.format_secondary_text(
            f"This will copy the theme to:\n{dest_path}\n\n"
            "Requires root privileges.\n\n"
            "Command to run:\n"
            f"sudo cp -r {self.current_theme_path} /usr/share/plymouth/themes/"
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            try:
                result = subprocess.run(
                    ['pkexec', 'cp', '-r', str(self.current_theme_path), '/usr/share/plymouth/themes/'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.show_message("Success", f"Theme '{theme_name}' installed successfully!")
                else:
                    self.show_message("Error", f"Failed to install theme:\n{result.stderr}", Gtk.MessageType.ERROR)
            except Exception as e:
                self.show_message("Error", f"Failed to install theme:\n{str(e)}", Gtk.MessageType.ERROR)

    def on_apply_clicked(self, button):
        if not hasattr(self, 'current_theme_path'):
            return
        theme_name = self.current_theme_path.name
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Apply '{theme_name}' as default?"
        )
        dialog.format_secondary_text(
            "This will:\n"
            "1. Install the theme (if not already installed)\n"
            "2. Set it as the default Plymouth theme\n"
            "3. Rebuild initramfs\n\n"
            "Requires root privileges.\n\n"
            "Commands to run:\n"
            f"sudo cp -r {self.current_theme_path} /usr/share/plymouth/themes/\n"
            f"sudo plymouth-set-default-theme -R {theme_name}"
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.apply_theme(theme_name)

    def apply_theme(self, theme_name):
        progress_dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text="Applying theme..."
        )
        progress_dialog.format_secondary_text("Please wait while the theme is being applied.")
        progress_dialog.show_all()
        while Gtk.events_pending():
            Gtk.main_iteration()
        try:
            result = subprocess.run(
                ['pkexec', 'cp', '-r', str(self.current_theme_path), '/usr/share/plymouth/themes/'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                progress_dialog.destroy()
                self.show_message("Error", f"Failed to copy theme:\n{result.stderr}", Gtk.MessageType.ERROR)
                return
            result = subprocess.run(
                ['pkexec', 'plymouth-set-default-theme', '-R', theme_name],
                capture_output=True,
                text=True
            )
            progress_dialog.destroy()
            if result.returncode == 0:
                self.show_message("Success", f"Theme '{theme_name}' has been applied!\n\nThe theme will be visible on your next boot.")
            else:
                self.show_message("Error", f"Failed to apply theme:\n{result.stderr}", Gtk.MessageType.ERROR)
        except Exception as e:
            progress_dialog.destroy()
            self.show_message("Error", f"Failed to apply theme:\n{str(e)}", Gtk.MessageType.ERROR)

    def show_message(self, title, message, msg_type=Gtk.MessageType.INFO):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_quit(self, widget):
        self.stop_animation()
        Gtk.main_quit()


def main():
    app = PlymouthViewer()
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
