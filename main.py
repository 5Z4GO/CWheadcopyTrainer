# Morse Trainer App v1.09

import os
import random
import numpy as np
import wave
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.properties import NumericProperty

WAV_DIR = '/storage/emulated/0/Documents/morse_audio'
WORDS_FILES = {
    'single': '/storage/emulated/0/Documents/common_words.txt',
    '2': '/storage/emulated/0/Documents/Two Word Phrases.txt',
    '3': '/storage/emulated/0/Documents/Three Word Phrases.txt',
    '4': '/storage/emulated/0/Documents/Four Word Phrases.txt',
}
VERSION = 'Morse Trainer v1.09'

MORSE_CODE = {
    'A': ".-", 'B': "-...", 'C': "-.-.", 'D': "-..", 'E': ".",
    'F': "..-.", 'G': "--.", 'H': "....", 'I': "..", 'J': ".---",
    'K': "-.-", 'L': ".-..", 'M': "--", 'N': "-.", 'O': "---",
    'P': ".--.", 'Q': "--.-", 'R': ".-.", 'S': "...", 'T': "-",
    'U': "..-", 'V': "...-", 'W': ".--", 'X': "-..-", 'Y': "-.--",
    'Z': "--.."
}

def text_to_morse(text):
    return ' '.join(MORSE_CODE.get(char.upper(), '') if char != ' ' else '/' for char in text)

def generate_tone(filename, morse_code, wpm=25, freq=750, fs=44100):
    dit_len = 1.2 / wpm
    dah_len = 3 * dit_len
    intra = dit_len
    inter = 3 * dit_len
    word_space = 7 * dit_len

    def tone(duration):
        t = np.linspace(0, duration, int(fs * duration), False)
        return 0.5 * np.sin(2 * np.pi * freq * t)

    def silence(duration):
        return np.zeros(int(fs * duration))

    audio = np.array([], dtype=np.float32)

    for char in morse_code:
        if char == '.':
            audio = np.concatenate((audio, tone(dit_len), silence(intra)))
        elif char == '-':
            audio = np.concatenate((audio, tone(dah_len), silence(intra)))
        elif char == ' ':
            audio = np.concatenate((audio, silence(inter)))
        elif char == '/':
            audio = np.concatenate((audio, silence(word_space)))

    audio = np.int16(audio * 32767)
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(fs)
        f.writeframes(audio.tobytes())

from kivy.uix.togglebutton import ToggleButton
class ConfigScreen(Screen):
    def _init_(self, **kwargs):
        super()._init_(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        layout.add_widget(Label(text='CW Headcopy Trainer by 5Z4GO', font_size=36))
        layout.add_widget(Label(text='Select WPM'))
        self.wpm_slider = Slider(min=5, max=50, value=25)
        self.wpm_label = Label(text=f"WPM: {int(self.wpm_slider.value)}")
        self.wpm_slider.bind(value=lambda s, v: setattr(self.wpm_label, 'text', f"WPM: {int(v)}"))
        layout.add_widget(self.wpm_slider)
        layout.add_widget(self.wpm_label)

        layout.add_widget(Label(text='Select Pitch (Hz)'))
        self.pitch_slider = Slider(min=300, max=1000, value=750)
        self.pitch_label = Label(text=f"Pitch: {int(self.pitch_slider.value)} Hz")
        self.pitch_slider.bind(value=lambda s, v: setattr(self.pitch_label, 'text', f"Pitch: {int(v)} Hz"))
        layout.add_widget(self.pitch_slider)
        layout.add_widget(self.pitch_label)

        layout.add_widget(Label(text='Select Phrase Length'))
        self.radio_layout = BoxLayout(orientation='vertical')
        self.selected_file = 'single'
        self.radio_buttons = []
        for name, label in [('single', 'Single Words'), ('2', '2 Word Phrases'), ('3', '3 Word Phrases'), ('4', '4 Word Phrases')]:
            btn = ToggleButton(text=label, group='file_select', size_hint_y=None, height=40)
            if name == 'single':
                btn.state = 'down'
            btn.bind(on_press=lambda b, n=name: setattr(self, 'selected_file', n))
            self.radio_layout.add_widget(btn)
        layout.add_widget(self.radio_layout)

        self.status = Label(text='')
        layout.add_widget(self.status)
        self.spinner = Spinner(text='Please wait...', size_hint=(1, 0.2))
        self.spinner.opacity = 0
        layout.add_widget(self.spinner)

        ok_btn = Button(text='OK', size_hint=(1, 0.3), background_color=(0, 0.6, 0.8, 1))
        ok_btn.bind(on_press=self.generate_audio)
        layout.add_widget(ok_btn)

        layout.add_widget(Label(text=VERSION, font_size=12))
        self.add_widget(layout)

    def generate_audio(self, instance):
        self.status.text = 'Generating audio...'
        self.spinner.opacity = 1
        Clock.schedule_once(self._generate_files, 0.1)

    def _generate_files(self, dt):
        wpm = int(self.wpm_slider.value)
        pitch = int(self.pitch_slider.value)
        filename = WORDS_FILES[self.selected_file]
        os.makedirs(WAV_DIR, exist_ok=True)
        with open(filename) as f:
            words = [line.strip() for line in f if line.strip()]
        self.words = random.sample(words, 100)
        self.files = []
        for i, word in enumerate(self.words):
            filepath = os.path.join(WAV_DIR, f'word_{i}.wav')
            morse = text_to_morse(word)
            generate_tone(filepath, morse, wpm=wpm, freq=pitch)
            self.files.append((word, filepath))
        self.manager.transition.direction = 'left'
        player = self.manager.get_screen('player')
        player.load_words(self.files, self.selected_file, wpm)
        self.manager.current = 'player'

class PlayerScreen(Screen):
    index = NumericProperty(0)

    def _init_(self, **kwargs):
        super()._init_(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.layout.add_widget(Label(text='CW Headcopy Trainer by 5Z4GO', font_size=36))
        self.word_label = Label(text='', font_size=48)
        self.layout.add_widget(self.word_label)
        self.progress = Label(text='')
        self.layout.add_widget(self.progress)
        btns = BoxLayout(size_hint=(1, 0.3), spacing=10)
        self.play_btn = Button(text='Play', background_color=(0.2, 0.6, 0.2, 1))
        self.play_btn.bind(on_press=self.play_word)
        btns.add_widget(self.play_btn)
        self.new_btn = Button(text='New Words', background_color=(0.8, 0.4, 0, 1))
        self.new_btn.bind(on_press=self.to_config)
        btns.add_widget(self.new_btn)
        self.exit_btn = Button(text='Exit', background_color=(0.6, 0, 0, 1))
        self.exit_btn.bind(on_press=App.get_running_app().stop)
        btns.add_widget(self.exit_btn)
        self.layout.add_widget(btns)
        self.status_line = Label(text='')
        self.layout.add_widget(self.status_line)
        self.add_widget(self.layout)

    def load_words(self, files, selection, wpm):
        self.index = 0
        self.files = files
        labels = {
            'single': 'Single Words',
            '2': '2 Word Phrases',
            '3': '3 Word Phrases',
            '4': '4 Word Phrases',
        }
        self.status_line.text = f"{VERSION} — {labels[selection]}, {wpm} WPM"
        self.update_display()

    def update_display(self):
        if self.index < len(self.files):
            self.word_label.text = ''
            self.progress.text = f'{self.index + 1} / {len(self.files)}'
        else:
            self.word_label.text = 'Done!'
            self.progress.text = ''

    def play_word(self, instance):
        if self.index < len(self.files):
            word, filepath = self.files[self.index]
            sound = SoundLoader.load(filepath)
            if sound:
                self.word_label.text = ''
                sound.play()
                Clock.schedule_once(lambda dt: self.reveal_word(word), sound.length+1)
            self.index += 1
            self.progress.text = f'{self.index} / {len(self.files)}'

    def reveal_word(self, word):
        self.word_label.text = word

    def to_config(self, instance):
        self.manager.transition.direction = 'right'
        self.manager.get_screen('config').spinner.opacity = 0
        self.manager.get_screen('config').status.text = ''
        self.manager.current = 'config'

class MorseApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(ConfigScreen(name='config'))
        sm.add_widget(PlayerScreen(name='player'))
        return sm

if _name_ == '_main_':
    MorseApp().run()