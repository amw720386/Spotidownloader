import requests
import re
import json
from yt_dlp import YoutubeDL
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
import threading
from kivy.clock import Clock
import os
from datetime import datetime

now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

try:
    from android.storage import primary_external_storage_path
    download_dir = os.path.join(primary_external_storage_path(), "Download")
except ImportError:
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

subfolder = f"Music/SpotiDownload-{now}"
full_path = os.path.join(download_dir, subfolder)
os.makedirs(full_path, exist_ok=True)

Window.clearcolor = (0.1, 0.1, 0.1, 1) 

class SpotiDownload(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        self.input_box = TextInput(
            hint_text="Paste Spotify song/album/playlist link here",
            multiline=False,
            size_hint_y=None,
            height=50,
            foreground_color=(1,1,1,1),
            background_color=(0.2,0.2,0.2,1),
            cursor_color=(1,1,1,1)
        )

        self.download_button = Button(
            text="Download",
            size_hint_y=None,
            height=50,
            background_color=(0.1,0.6,0.2,1)
        )
        self.download_button.bind(on_press=self.download_handler)

        self.log_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))

        self.scroll = ScrollView(size_hint=(1, 1))
        self.scroll.add_widget(self.log_layout)

        self.add_widget(self.input_box)
        self.add_widget(self.download_button)
        self.add_widget(self.scroll)
    
    def safe_log(self, message, success=True):
        Clock.schedule_once(lambda dt: self.log(message, success))

    def log(self, message, success=True):
        color = (0.5, 1, 0.5, 1) if success else (1, 0.5, 0.5, 1)
        label = Label(
            text=message,
            size_hint_y=None,
            height=30,
            color=color,
            halign="left",
            valign="middle"
        )
        label.bind(size=lambda s, *a: setattr(s, 'text_size', s.size))
        self.log_layout.add_widget(label)

    def get_titles(self, url):
        if "spotify.com" not in url:
            self.log("Not a Spotify URL", False)
            print("Not a Spotify URL", False)
            return []

        try:
            oembed = requests.get("https://open.spotify.com/oembed", params={"url": url})
            if not oembed.ok:
                self.log("oEmbed request failed", False)
                print("oEmbed request failed", False)
                return []

            data = oembed.json()
            iframe_url = data.get("iframe_url", "")
            title = data.get("title", "")

            if "/track/" in url:
                return [title + " lyric video"]

            page = requests.get(iframe_url, headers={"User-Agent": "Mozilla/5.0"})
            html = page.text

            match = re.search(r'>{\s*"props":.*?</script>', html)
            if not match:
                self.log("Couldn't find embedded JSON", False)
                print("Couldn't find embedded JSON", False)
                return []

            raw_json = match.group(0)[1:-9]
            parsed = json.loads(raw_json)

            track_list = parsed["props"]["pageProps"]["state"]["data"]["entity"]["trackList"]
            return [f"{track['title']} {track['subtitle']} lyric video" for track in track_list]

        except Exception as e:
            self.log(f"Error parsing Spotify data: {e}", False)
            print(f"Error parsing Spotify data: {e}", False)
            return []

    def run_download(self, titles):
        for title in titles:
            success = False
            for i in range(1, 6):
                query = f"ytsearch{i}:{title}"

                output_template = os.path.join(full_path, f"{title[:-12]}.%(ext)s")
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]',
                    'default_search': None,
                    'outtmpl': output_template,
                    'quiet': True,
                    'no_warnings': True,
                }

                try:
                    self.safe_log(f"Searching: {query}")
                    print(f"Searching: {query}")
                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download([query])
                    self.safe_log(f"Downloaded: {title}")
                    print(f"Downloaded: {title}")
                    success = True
                    break
                except Exception as e:
                    continue

            if not success:
                self.safe_log(f"Skipped: {title} — no .m4a found", False)
                print(f"Skipped: {title} — no .m4a found", False)


    def download_handler(self, instance):
        url = self.input_box.text.strip()
        if not url:
            self.safe_log("Please enter a Spotify link", False)
            print("Please enter a Spotify link", False)
            return

        self.log_layout.clear_widgets()
        self.safe_log("Fetching track info...")
        print("Fetching track info...")

        titles = self.get_titles(url)
        if not titles:
            self.safe_log("No valid titles found", False)
            print("No valid titles found", False)
            return

        self.safe_log(f"Found {len(titles)} track(s). Starting download...")
        print(f"Found {len(titles)} track(s). Starting download...")

        threading.Thread(target=self.run_download, args=(titles,), daemon=True).start()

class MyApp(App):
    def build(self):
        return SpotiDownload()

if __name__ == '__main__':
    MyApp().run()
