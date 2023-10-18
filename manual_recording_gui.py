"""
Author: Gildas Lefur (a.k.a. "mjitkop" in the Channels DVR forums)

Description: This script provides the capability to create manual recordings on a 
             Channels DVR server. 

Disclaimer: this is an unofficial script that is NOT supported by the developers
            of Channels DVR.

Version History:
- 2023.08.29.1723: First public release
- 2023.08.29.2345: FIXED: the IP address and port numbers entered by the user were
                          ignored and the default values were used
                   NEW: save the IP address and port number so the user doesn't
                        have to reenter them when reopening the app
- 2023.10.15.1914: NEW: button to create a JSON file with the payload, and
                        display the command line that can be copied by the user
- 2023.10.17.2230: IMPROVED: changed the layout so that the window is now wider
                             and not as tall. It will look better on some screens
"""

################################################################################
#                                                                              #
#                                   IMPORTS                                    #
#                                                                              #
################################################################################

import os
import requests
import tkinter as tk
from CDVR_Support import DEFAULT_PORT_NUMBER, LOOPBACK_ADDRESS, convert_to_epoch_time
from datetime import datetime, timedelta
from PIL import Image, ImageTk
from time import sleep
from tkinter import END, font

################################################################################
#                                                                              #
#                                  CONSTANTS                                   #
#                                                                              #
################################################################################

# Color definitions
BLUE   = "#2012B3"
ORANGE = "#FFAD00"

BACKGROUND_COLOR = BLUE
IMAGE_URL        = "https://tmsimg.fancybits.co/assets/p9467679_st_h6_aa.jpg"
LOCAL_IMAGE      = 'art.jpg'
TEXT_COLOR       = ORANGE

# Other constants
BOLD_FONT       = ("Helvetica", 12, "bold")
LABEL_POSITION  = {1: 0, 2: 2, 3: 4, 4: 6, 5: 8, 6: 10}
NORMAL_FONT     = ("Helvetica", 12, "normal")
OBJECT_POSITION = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11}

DEFAULT_SERVER_SETTINGS_FILE = 'default_cdvr_server_settings.txt'

################################################################################
#                                                                              #
#                               GLOBAL VARIABLES                               #
#                                                                              #
################################################################################

server_ip_address  = None
server_port_number = None
widgets            = {}

#
# Window management
#

class DropDownSelector():
  def __init__(self, frame, name, values, row, order, action) -> None:
    self.frame  = frame
    self.name   = name
    self.order  = order
    self.row    = row
    self.values = values
    self.value  = tk.StringVar(self.frame)
    self.option = tk.OptionMenu(self.frame, self.value, *self.values, command=action)

    self.create()

  def create(self):
    self.create_label()
    self.create_dropdown()

  def create_label(self):
    label = tk.Label(self.frame, bg = BACKGROUND_COLOR, text = f"{self.name}", fg = TEXT_COLOR, font = BOLD_FONT)
    label.grid(row = self.row, column = LABEL_POSITION[self.order], padx = 5, pady = 10, sticky = 'e')

  def create_dropdown(self):
    my_font = font.Font(size = 13)
    self.option.config(font = my_font)
    self.option.grid(row = self.row, column = OBJECT_POSITION[self.order], padx = 5, pady = 10, sticky = "w")

  def get_value(self):
    return int(self.value.get())

  def set_value(self, value):
    self.value.set(value)

class DateWidget():
  def __init__(self, frame, action):
    self.action = action
    self.day   = DropDownSelector(frame, "/",   range(1, 32), 0, 2, action)
    self.month = DropDownSelector(frame, "Day:", range(1, 13), 0, 1, action)
    self.year  = DropDownSelector(frame, "/",  (2023, 2024), 0, 3, action)

  def get_date(self):
    return {'year': self.year.get_value(), 'month': self.month.get_value(), 'day': self.day.get_value()}
  
  def set_date(self, desired_date):
    self.day.set_value(desired_date['day'])
    self.month.set_value(desired_date['month'])
    self.year.set_value(desired_date['year'])

class TimeWidget():
  def __init__(self, frame, action):
    self.action  = action
    self.hour    = DropDownSelector(frame, "Time:",    range(0, 24), 0, 4, action)
    self.minutes = DropDownSelector(frame, ":", range(0, 60), 0, 5, action)
    self.seconds = DropDownSelector(frame, ":", range(0, 60), 0, 6, action)

  def get_time(self):
    return {'hour': self.hour.get_value(), 'minutes': self.minutes.get_value(), 'seconds': self.seconds.get_value()}
  
  def set_time(self, desired_time):
    self.hour.set_value(desired_time['hour'])
    self.minutes.set_value(desired_time['minutes'])
    self.seconds.set_value(desired_time['seconds'])


def start_main_menu():
  global widgets

  window_main_menu = tk.Tk()
  window_main_menu.title("Channels DVR Manual Recording")

  frame = tk.Frame(window_main_menu, bg=BACKGROUND_COLOR)
  frame.pack()

  #
  # Define all the subframes that are in the main frame
  #
  server_info_frame = tk.LabelFrame(frame, bg=BACKGROUND_COLOR, text=" Server Connection ", fg=TEXT_COLOR, font=BOLD_FONT)
  server_info_frame.grid(row=0, column=0, padx=10, pady=10)

  program_info_frame = tk.LabelFrame(frame, bg=BACKGROUND_COLOR, text=" Program Info ", fg=TEXT_COLOR, font=BOLD_FONT)
  program_info_frame.grid(row=1, column=0, padx=10, pady=10)

  start_frame = tk.LabelFrame(frame, bg=BACKGROUND_COLOR, text=" Start ", fg=TEXT_COLOR, font=BOLD_FONT)
  start_frame.grid(row=2, column=0, padx=10, pady=10)

  duration_frame = tk.LabelFrame(frame, bg=BACKGROUND_COLOR, text=" Duration ", fg=TEXT_COLOR, font=BOLD_FONT)
  duration_frame.grid(row=3, column=0, padx=10, pady=10)

  stop_frame = tk.LabelFrame(frame, bg=BACKGROUND_COLOR, text=" Stop ", fg=TEXT_COLOR, font=BOLD_FONT)
  stop_frame.grid(row=4, column=0, padx=10, pady=10)

  button_frame = tk.LabelFrame(frame, bg=BACKGROUND_COLOR, text=" Actions ", fg=TEXT_COLOR, font=BOLD_FONT)
  button_frame.grid(row=5, column=0, padx=10, pady=10)

  subframes = (program_info_frame, start_frame, duration_frame, stop_frame, button_frame)

  #
  # Frame: Server Connection
  #

  ip_address_label = tk.Label(server_info_frame, bg=BACKGROUND_COLOR, text="IP address :", fg=TEXT_COLOR, font=BOLD_FONT)
  ip_address_label.grid(row=0, column=0, sticky='e')

  read_default_server_settings_from_file()
  if server_ip_address:
    initial_ip_address  = server_ip_address
    initial_port_number = server_port_number
  else:
    initial_ip_address  = LOOPBACK_ADDRESS
    initial_port_number = DEFAULT_PORT_NUMBER

  ip_address = tk.StringVar(value=initial_ip_address)
  ip_address_entry = tk.Entry(server_info_frame, textvariable=ip_address, font=NORMAL_FONT, width=14)
  ip_address_entry.grid(row=0, column=1, sticky='w')
      
  port_number_label = tk.Label(server_info_frame, bg=BACKGROUND_COLOR, text="Port number :", fg=TEXT_COLOR, font=BOLD_FONT)
  port_number_label.grid(row=0, column=2, sticky='e')

  port_number = tk.StringVar(value=initial_port_number)
  port_number_entry = tk.Entry(server_info_frame, textvariable=port_number, font=NORMAL_FONT, width=4)
  port_number_entry.grid(row=0, column=3, sticky='w')

  connect_button = tk.Button(server_info_frame, text="Connect", font=NORMAL_FONT, \
        command=lambda:update_server_status(ip_address_entry.get(), port_number_entry.get(), \
                                            server_status_value, subframes, (json_button, schedule_button)))
  connect_button.grid(row=0, column=4)

  server_status_label = tk.Label(server_info_frame, bg=BACKGROUND_COLOR, text="Status :", fg=TEXT_COLOR, font=BOLD_FONT)
  server_status_label.grid(row=0, column=5, sticky='e')
  server_status_value = tk.Label(server_info_frame, text="No Connection", font=NORMAL_FONT)
  server_status_value.grid(row=0, column=6, sticky='w')
  
  # Space out all the widgets
  for widget in server_info_frame.winfo_children():
    widget.grid_configure(padx=5, pady=5)

  #
  #  Frame: Program Info
  #

  # Labels
  channel_label = tk.Label(program_info_frame, text="Channel :", bg=BACKGROUND_COLOR, fg=TEXT_COLOR, font=BOLD_FONT)
  channel_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")

  program_name_label = tk.Label(program_info_frame, text="Name of program :", bg=BACKGROUND_COLOR, fg=TEXT_COLOR, font=BOLD_FONT)
  program_name_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")

  episode_name_label = tk.Label(program_info_frame, text="Name of episode :", bg=BACKGROUND_COLOR, fg=TEXT_COLOR, font=BOLD_FONT)
  episode_name_label.grid(row=2, column=0, padx=10, pady=5, sticky="e")

  image_url_label = tk.Label(program_info_frame, text="Image URL :", bg=BACKGROUND_COLOR, fg=TEXT_COLOR, font=BOLD_FONT)
  image_url_label.grid(row=3, column=0, padx=10, pady=5, sticky="e")

  image_label = tk.Label(program_info_frame, bg=BACKGROUND_COLOR)
  image_label.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
  
  # Buttons
  load_image_bt = tk.Button(program_info_frame, text='Preview', font=NORMAL_FONT, command=lambda: load_image(image_url_entry.get(), image_label))
  load_image_bt.grid(row=4, column=0, padx=10, pady=5, sticky='e')

  # Entries
  channel_entry = tk.Entry(program_info_frame, font=NORMAL_FONT, width=5, justify='center')
  channel_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
  channel_entry.insert(0, '6002')
  widgets['channel_number'] = channel_entry

  program_name_entry = tk.Entry(program_info_frame, font=NORMAL_FONT, width=53, justify='left')
  program_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
  program_name_entry.insert(0, 'Manual Recordings')
  widgets['program_name'] = program_name_entry

  episode_name_entry = tk.Entry(program_info_frame, font=NORMAL_FONT, width=53, justify='left')
  episode_name_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
  episode_name_entry.insert(0, 'Manual Recording')
  widgets['episode_name'] = episode_name_entry

  image_url_entry = tk.Entry(program_info_frame, font=NORMAL_FONT, width=53, justify='left')
  image_url_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
  image_url_entry.insert(0, IMAGE_URL)
  widgets['image_url'] = image_url_entry

  #
  # Frame: Start Day and Time
  #

  in_one_hour = datetime.now() + timedelta(hours=1)
  
  start_date_widget  = DateWidget(start_frame, update_stop_date_and_time)
  widgets['start_date'] = start_date_widget
  start_date_widget.set_date({'year': in_one_hour.year, 'month': in_one_hour.month, 'day': in_one_hour.day})
  
  start_time_widget = TimeWidget(start_frame, update_stop_date_and_time)
  widgets['start_time'] = start_time_widget
  start_time_widget.set_time({'hour': in_one_hour.hour, 'minutes': 0, 'seconds': 0})
  
  #
  # Frame: Duration
  #

  duration_widget = TimeWidget(duration_frame, update_stop_date_and_time)
  widgets['duration'] = duration_widget
  duration_widget.set_time({'hour': 0, 'minutes': 30, 'seconds': 0})

  #
  # Frame: Stop Day and Time
  #
  initial_start = datetime(year=in_one_hour.year, month=in_one_hour.month, day=in_one_hour.day, hour=in_one_hour.hour, minute=0, second=0)
  initial_stop = initial_start + timedelta(minutes=30)

  stop_day_widget  = DateWidget(stop_frame, update_duration)
  widgets['stop_date'] = stop_day_widget
  stop_day_widget.set_date({'year': initial_stop.year, 'month': initial_stop.month, 'day': initial_stop.day})

  stop_time_widget = TimeWidget(stop_frame, update_duration)
  widgets['stop_time'] = stop_time_widget
  stop_time_widget.set_time({'hour': initial_stop.hour, 'minutes': initial_stop.minute, 'seconds': initial_stop.second})

  #
  # JSON button
  #

  json_button = tk.Button(button_frame, text="Create JSON File", font=NORMAL_FONT, bd=3, command=lambda:save_json_payload_to_file(cli_entry))
  json_button.grid(row=0, column=0, padx=15, pady=10, sticky="w")
  
  #
  # Schedule button
  #

  schedule_button = tk.Button(button_frame, text="Schedule Manual Recording", font=NORMAL_FONT, bd=3, command=lambda:schedule_recording(schedule_button))
  schedule_button.grid(row=0, column=1, padx=15, pady=10, sticky="e")

  #
  # Entry to display the CLI and the user can copy
  #
  cli_entry = tk.Entry(button_frame, font=NORMAL_FONT, width=80, justify='left')
  cli_entry.grid(row=1, columnspan=2, padx=15, pady=5, sticky="w")
  cli_entry.insert(0, '(the command will be displayed here)')

  
  disable_subframes_and_buttons(subframes, (json_button, schedule_button))
  
  # Launch the window    
  window_main_menu.mainloop()


################################################################################
#                                                                              #
#                                  FUNCTIONS                                   #
#                                                                              #
################################################################################

def convert_seconds_to_hms(seconds: int) -> tuple:
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return (hours, minutes, seconds)

def get_duration_in_seconds():
  start_dt = get_start_dt()
  stop_dt  = get_stop_dt()

  duration = (stop_dt - start_dt).seconds

  return duration

def get_start_dt():
  start = get_start_info()

  return datetime(year=start['year'], month=start['month'], day=start['day'],
                  hour=start['hour'], minute=start['minutes'], second=start['seconds'])

def get_start_info():
  start_date = widgets['start_date'].get_date()
  start_time = widgets['start_time'].get_time()

  return {'year': start_date['year'], 'month': start_date['month'], 'day': start_date['day'],
          'hour': start_time['hour'], 'minutes': start_time['minutes'], 'seconds': start_time['seconds']}

def get_stop_dt():
  stop = get_stop_info()

  return datetime(year=stop['year'], month=stop['month'], day=stop['day'],
                  hour=stop['hour'], minute=stop['minutes'], second=stop['seconds'])

def get_stop_info():
  stop_date = widgets['stop_date'].get_date()
  stop_time = widgets['stop_time'].get_time()

  return {'year': stop_date['year'], 'month': stop_date['month'], 'day': stop_date['day'],
          'hour': stop_time['hour'], 'minutes': stop_time['minutes'], 'seconds': stop_time['seconds']}

def create_json_payload():
  json_payload = {}
  json_payload['Airing'] = {}

  program_info = get_program_info()
  start_info   = get_start_info()

  channel_number = program_info['channel_number']
  duration       = get_duration_in_seconds()
  day            = start_info['day']
  episode_name   = program_info['episode_name']
  hour           = start_info['hour']
  image_url      = program_info['image_url']
  minutes        = start_info['minutes']
  month          = start_info['month']
  program_name   = program_info['program_name']
  seconds        = start_info['seconds']
  year           = start_info['year']

  start_time = convert_to_epoch_time(year, month, day, hour, minutes, seconds)

  json_payload['Name']     = program_name
  json_payload["Time"]     = start_time 
  json_payload["Duration"] = duration
  json_payload["Channels"] = [channel_number]
  json_payload["Airing"]["Source"]       = "manual" 
  json_payload["Airing"]["Channel"]      = channel_number
  json_payload["Airing"]["Time"]         = start_time
  json_payload["Airing"]["Duration"]     = duration
  json_payload["Airing"]["Title"]        = program_name
  json_payload["Airing"]["EpisodeTitle"] = episode_name
  json_payload["Airing"]["Summary"]      = f"Manual recording of channel {channel_number} on {year}-{month:02d}-{day:02d} @ {hour:02d}:{minutes:02d}:{seconds:02d} for {duration} seconds."
  json_payload["Airing"]["SeriesID"]     = "MANUAL"
  json_payload["Airing"]["ProgramID"]    = f"MAN{start_time}"
  json_payload["Airing"]["Image"]        = image_url

  return json_payload

def download_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"Image downloaded and saved as {filename}")
    else:
        print("Failed to download image")

def enable_subframes_and_buttons(subframes, buttons):
  for frame in subframes:
    for child in frame.winfo_children():
      child.configure(state='normal')

  for button in buttons:
    button.config(state='normal')

def disable_subframes_and_buttons(subframes, buttons):
  for frame in subframes:
    for child in frame.winfo_children():
      child.configure(state='disable')
 
  for button in buttons:
    button.config(state='disable')

def get_program_info():
  program_info = {}

  program_info['channel_number'] = widgets['channel_number'].get()
  program_info['program_name']   = widgets['program_name'].get()
  program_info['episode_name']   = widgets['episode_name'].get()
  program_info['image_url']      = widgets['image_url'].get()

  return program_info

def read_default_server_settings_from_file():
  global server_ip_address
  global server_port_number

  if os.path.exists(DEFAULT_SERVER_SETTINGS_FILE):
    with open(DEFAULT_SERVER_SETTINGS_FILE, 'r') as f:
      default = f.read()
    
    server_ip_address  = default.split(':')[0]
    server_port_number = default.split(':')[1]

def resize_image(local_image, width=144, height=108):
  resized_image = Image.open(local_image).resize((width, height))
                                                  
  return ImageTk.PhotoImage(resized_image)

def save_default_server_settings_to_file(ip, port):
  with open(DEFAULT_SERVER_SETTINGS_FILE, 'w') as f:
    f.write(f'{ip}:{port}')

def update_duration(ignored_argument):
  global widgets

  duration = get_duration_in_seconds()

  hours, minutes, seconds = convert_seconds_to_hms(duration)

  widgets['duration'].set_time({'hour': hours, 'minutes': minutes, 'seconds': seconds})

def update_stop_date_and_time(ignored_input):
  start_date_widget = widgets.get('start_date', None)
  start_time_widget = widgets.get('start_time', None)
  duration_widget   = widgets.get('duration', None)
  stop_date_widget  = widgets.get('stop_date', None)
  stop_time_widget  = widgets.get('stop_time', None)

  if start_date_widget and start_time_widget and duration_widget and stop_date_widget and stop_time_widget:
    start_date = start_date_widget.get_date()
    start_time = start_time_widget.get_time()
    duration   = duration_widget.get_time()
    
    start_dt = datetime(year=start_date['year'], month=start_date['month'], day=start_date['day'],
                        hour=start_time['hour'], minute=start_time['minutes'], second=start_time['seconds'])
    
    duration_dt = timedelta(hours=duration['hour'], minutes=duration['minutes'], seconds=duration['seconds'])

    stop_dt = start_dt + duration_dt

    stop_date_widget.set_date({'year': stop_dt.year, 'month': stop_dt.month, 'day': stop_dt.day})
    stop_time_widget.set_time({'hour': stop_dt.hour, 'minutes': stop_dt.minute, 'seconds': stop_dt.second})

#
# Button commands
#

def load_image(image_url, image_label):
  download_image(image_url, LOCAL_IMAGE)
  
  tk_image = resize_image(LOCAL_IMAGE)
  
  image_label.configure(image=tk_image)
  image_label.image = tk_image

def update_server_status(ip_address, port_number, status_label, subframe_list, buttons):
  global server_ip_address
  global server_port_number

  url = f'http://{ip_address}:{port_number}/dvr'

  try:
    response = requests.get(url)
  except:
    response = None

  if response and response.status_code == 200:
    status_label.config(text="Connected")
    server_ip_address  = ip_address
    server_port_number = port_number
    enable_subframes_and_buttons(subframe_list, buttons)
    save_default_server_settings_to_file(server_ip_address, server_port_number)

  else:
    status_label.config(text="Not Connected")
    disable_subframes_and_buttons(subframe_list, buttons)

def reset(schedule_button):
  global widgets

  in_one_hour = datetime.now() + timedelta(hours=1)
  
  widgets['start_date'].set_date({'year': in_one_hour.year, 'month': in_one_hour.month, 'day': in_one_hour.day})
  widgets['start_time'].set_time({'hour': in_one_hour.hour, 'minutes': 0, 'seconds': 0})
  
  widgets['duration'].set_time({'hour': 0, 'minutes': 30, 'seconds': 0})

  initial_start = datetime(year=in_one_hour.year, month=in_one_hour.month, day=in_one_hour.day, hour=in_one_hour.hour, minute=0, second=0)
  initial_stop = initial_start + timedelta(minutes=30)

  widgets['stop_date'].set_date({'year': initial_stop.year, 'month': initial_stop.month, 'day': initial_stop.day})
  widgets['stop_time'].set_time({'hour': initial_stop.hour, 'minutes': initial_stop.minute, 'seconds': initial_stop.second})

  schedule_button.config(text='Schedule')

def save_json_payload_to_file(cli_field):
  json_payload = create_json_payload()

  title = json_payload['Airing']['Title'].lower().replace(' ', '_')
  episode_title = json_payload['Airing']['EpisodeTitle'].lower().replace(' ', '_')
  filename = title + '_' + episode_title + '.json'

  with open(filename, 'w') as json_file:
    json_file.write(str(json_payload))

  cli_field.delete(0, END)
  cli_field.insert(0, f'curl -XPOST --data-binary @{filename} "{server_ip_address}:{server_port_number}/dvr/jobs/new"')

def schedule_recording(schedule_button):
  json_payload = create_json_payload()

  print(json_payload)

  url = f'http://{server_ip_address}:{server_port_number}/dvr/jobs/new'
  response = requests.post(url, json=json_payload)

  print(response.status_code)
  print(response.reason)
  print(response.text)

  schedule_button.config(text=response.reason)
  schedule_button.config(command=lambda:reset(schedule_button))

################################################################################
#                                                                              #
#                                 MAIN PROGRAM                                 #
#                                                                              #
################################################################################

if __name__ == "__main__":
  start_main_menu()
