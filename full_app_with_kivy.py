from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
import json
import os
import pandas as pd
from datetime import datetime
from time import sleep
json_file_path = 'year_counter.json'
if not os.path.exists('Output'):
    os.makedirs('Output')

def convert_to_excel(input_file, output_file, update_progress):
    progress_list = []

    def safe_update_progress(value, message):
        progress_list.append((value, message))
        progress_list.sort(key=lambda x: x[0])
        
    

    try:
        safe_update_progress(5, "Input file not found. System trying with input file 1...")
        with open(input_file, 'r') as file:
            data = json.load(file)
        safe_update_progress(10, "Loading JSON data...")

        safe_update_progress(30, "Processing laps...")
        laps = []
        leaderboard = []
        best_lap_time = min([line['timing']['bestLap'] for line in data['sessionResult']['leaderBoardLines']])
        total_participants = len(data['sessionResult']['leaderBoardLines'])
        rank_points = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1] + [0] * (total_participants - 10)

        for lap in data['laps']:
            laps.append({
                'Car ID': lap['carId'],
                'Driver Index': lap['driverIndex'],
                'Valid for Best': lap['isValidForBest'],
                'Lap Time (ms)': lap['laptime'],
                'Split 1 (ms)': lap['splits'][0] if len(lap['splits']) > 0 else None,
                'Split 2 (ms)': lap['splits'][1] if len(lap['splits']) > 1 else None,
                'Split 3 (ms)': lap['splits'][2] if len(lap['splits']) > 2 else None
            })

        laps_df = pd.DataFrame(laps)

        safe_update_progress(50, "Calculating leaderboard data...")
        invalid_laps = laps_df[~laps_df['Valid for Best']].groupby('Car ID').size().to_dict()

        for rank, entry in enumerate(data['sessionResult']['leaderBoardLines'], start=1):
            car = entry['car']
            timing = entry['timing']
            penalties = invalid_laps.get(car['carId'], 0)
            total_points = 25 + (5 if rank == 1 else 0) + (5 if rank <= 3 else 0) + (5 if timing['bestLap'] == best_lap_time else 0)
            total_points += rank_points[rank - 1] - penalties

            public_multiplier = 0.00927 * x + 1.04365
            public_points = round(total_points * public_multiplier)

            leaderboard.append({
                'Car ID': car['carId'],
                'Driver Name': f"{car['drivers'][0]['firstName']} {car['drivers'][0]['lastName']}",
                'Car Model': car['carModel'],
                'Participation': "Yes",
                'Pole': 1 if rank == 1 else 0,
                'Podium': True if rank <= 3 else None,
                'Winner': True if rank == 1 else None,
                'Best Lap': "Best" if timing['bestLap'] == best_lap_time else None,
                'ABL': "Best" if rank == 1 else None,
                'Rank Point': rank_points[rank - 1],
                'Penalty': -penalties,
                'Total Number of Points': total_points,
                'Public': public_points,
                'Cup Category': car['cupCategory'],
                'Race Number': car['raceNumber'],
                'Best Lap (ms)': timing['bestLap'],
                'Total Time (ms)': timing['totalTime'],
                'Lap Count': timing['lapCount']
            })

        leaderboard_df = pd.DataFrame(leaderboard)

        safe_update_progress(80, "Writing data to Excel...")
        with pd.ExcelWriter(output_file) as writer:
            laps_df.to_excel(writer, sheet_name='Laps', index=False)
            leaderboard_df.to_excel(writer, sheet_name='Leaderboard', index=False)

        safe_update_progress(100, f"File generation complete! ")
        for progress_value, progress_message in progress_list:
            update_progress(progress_value, progress_message)
    except FileNotFoundError:
        year_data['current_file'] -= 1
        year_data[current_year] -= 1
        i = year_data['current_file']

        if i > 0:
            input_file = f'Input/input{i}.txt'
            output_file = f'Output/Points_course_output{i}.xlsx'
            safe_update_progress(10, f"Retrying with input file: {input_file}...")
            convert_to_excel(input_file, output_file, update_progress)
            with open(json_file_path, 'w') as f:
                json.dump(year_data, f, indent=4)
        else:
            safe_update_progress(5, "No more previous files to try.")
            raise ValueError("No more previous files to try.")
    except json.JSONDecodeError:
        safe_update_progress(5, "Error parsing JSON data. Ensure the input file is valid.")
        raise ValueError("Error parsing JSON data. Ensure the input file is valid.")
    except KeyError as e:
        safe_update_progress(5, f"Missing key in JSON data: {e}")
        raise ValueError(f"Missing key in JSON data: {e}")


class RaceApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.padding = 80
        self.spacing = 80

        self.add_widget(Label(text="Enter Race Time (minutes):", size_hint=(1, 0.1)))
        self.race_time_input = TextInput(hint_text="Race Time", multiline=False, size_hint=(1, 0.1))
        self.add_widget(self.race_time_input)

        self.add_widget(Label(text="Regen:", size_hint=(0.4, 0.1)))
        self.regen_toggle = ToggleButton(text="Off", size_hint=(0.5, 0.1))
        self.regen_toggle.bind(on_press=self.toggle_regen)
        self.add_widget(self.regen_toggle)

        self.progress_bar = ProgressBar(max=100, size_hint=(1, 0.1))
        self.add_widget(self.progress_bar)
        self.feedback_label = Label(text="", size_hint=(1, 0.5))
        self.add_widget(self.feedback_label)

        self.generate_button = Button(text="Generate", size_hint=(1, 0.2))
        self.generate_button.bind(on_press=self.generate_file)
        self.add_widget(self.generate_button)

        self.regen = False

    def toggle_regen(self, instance):
        self.regen = not self.regen
        instance.text = "On" if self.regen else "Off"

    def update_progress(self, value, message):
        self.progress_bar.value = value
        Clock.schedule_once(lambda dt: self.show_message(message), 5)

    def show_message(self, message):
        self.feedback_label.text = message
        Clock.schedule_once(lambda dt: self.clear_message(), 5)

    def clear_message(self):
        self.feedback_label.text = ""

    def generate_file(self, instance):
        global x, year_data, current_year

        try:
            x = int(self.race_time_input.text)
        except ValueError:
            self.feedback_label.text = "Enter a valid race time!"
            return

        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as f:
                year_data = json.load(f)
        else:
            year_data = {'current_file': 0}

        current_year = str(datetime.now().year)
        if not self.regen:
            year_data['current_file'] += 1
            year_data[current_year] = year_data.get(current_year, 0) + 1

        i = year_data['current_file']
        with open(json_file_path, 'w') as f:
            json.dump(year_data, f, indent=4)

        input_file = f'Input/input{i}.txt'
        output_file = f'Output/Points_course_output{i}.xlsx'

        try:
            self.update_progress(0, "Starting file generation...")
            convert_to_excel(input_file, output_file, self.update_progress)
            self.feedback_label.text = f"File generated: {output_file}"
        except ValueError as e:
            self.feedback_label.text = f"Error: {e}"


class RaceAppApp(App):
    def build(self):
        return RaceApp()


if __name__ == '__main__':
    RaceAppApp().run()