import os
import json
import threading
import time
from tkinter import filedialog, simpledialog, StringVar, Listbox
from customtkinter import CTk, CTkButton, CTkLabel, CTkProgressBar, CTkEntry, CTkTabview, CTkFrame, set_appearance_mode, set_default_color_theme
from moviepy.editor import VideoFileClip, concatenate_videoclips
from yt_dlp import YoutubeDL

# JSON dosyasının tam yolu
progress_file = 'progress_1.json'


set_appearance_mode("Dark")  
set_default_color_theme("green")

def load_progress():
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as file:
                progress_data = json.load(file)
                print(f"Progress loaded: {progress_data}")
                return progress_data
        except Exception as e:
            print(f"Error reading progress file: {e}")
    else:
        print(f"No progress file found at {progress_file}")
        return []

def save_progress(group_index, last_file):
    progress = load_progress()
    if not isinstance(progress, list):
        progress = []
    progress.append({'group_index': group_index, 'last_file': last_file})
    try:
        with open(progress_file, 'w') as file:
            json.dump(progress, file)
            print(f"Progress saved: {progress}")
    except Exception as e:
        print(f"Error writing progress file: {e}")

def get_last_file():
    progress = load_progress()
    if progress:
        last_entry = progress[-1]
        return last_entry.get('last_file', 'No file processed yet.')
    return 'No file processed yet.'

def select_videos():
    filepaths = filedialog.askopenfilenames(
        title="Select Videos",
        filetypes=(("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.mpeg *.mpg"), ("All files", "*.*"))
    )
    return filepaths

def merge_videos(filepaths, output_path):
    video_clips = []
    for video in filepaths:
        try:
            clip = VideoFileClip(video)
            video_clips.append(clip)
            print(f"Loaded video: {video}")
        except Exception as e:
            print(f"Error loading video {video}: {e}")
    
    if video_clips:
        try:
            final_clip = concatenate_videoclips(video_clips)
            final_clip.write_videofile(output_path, codec="libx264", preset='fast', bitrate='500k')
            print(f"Video written to {output_path}")
            return output_path  # Return the output path
        except Exception as e:
            print(f"Error writing the final video: {e}")
    else:
        print("No videos to merge.")
    return None

def merge_groups(grouped_files, final_output_directory):
    progress = load_progress()
    last_processed_group = max([entry['group_index'] for entry in progress]) if progress else -1
    print(f"Birleştirilen grubun en son dosyası: {last_processed_group}")

    for i, group in enumerate(grouped_files):
        if i <= last_processed_group:
            continue
        if not group:
            continue
        first_file_mod_time = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(os.path.getmtime(group[0])))
        group_output_path = os.path.join(final_output_directory, f"group_{i+1}_{first_file_mod_time}.mp4")
        last_file = merge_videos(group, group_output_path)
        if last_file:
            save_progress(i, last_file)
            last_file_label.set(f"Last processed file: {os.path.basename(last_file)}")
            merged_files_listbox.insert('end', os.path.basename(last_file))  # Dosya adını kutuya ekle
        print(f"Processed group {i}, progress saved.")

def on_select_button_click():
    global selected_files
    selected_files = select_videos()
    if selected_files:
        num_files.set(f"Selected {len(selected_files)} files.")
        file_listbox.delete(0, 'end')
        for file in selected_files:
            file_listbox.insert('end', os.path.basename(file))
    else:
        num_files.set("No files selected.")

def on_merge_button_click():
    if selected_files:
        output_directory = filedialog.askdirectory(title="Select Output Directory")
        if output_directory:
            grouped_files = [selected_files[i:i + 3] for i in range(0, len(selected_files), 3)]
            threading.Thread(target=merge_groups, args=(grouped_files, output_directory)).start()
            num_files.set(f"Merged files into {output_directory}")
        else:
            num_files.set("Output directory not selected.")
    else:
        num_files.set("No files selected to merge.")

def reset_app():
    num_files.set("Selected 0 files.")
    progress.set(0)
    merge_status.set("")
    split_status.set("")
    file_listbox.delete(0, 'end')
    merged_files_listbox.delete(0, 'end') 
    global selected_files
    selected_files = []

def exit_app():
    root.quit()

def reset_progress():
    try:
        with open(progress_file, 'w') as file:
            json.dump([], file)
            print("Progress has been reset.")
        last_file_label.set("En son birleştirilen video: No file processed yet.")
        merged_files_listbox.delete(0, 'end')
    except Exception as e:
        print(f"Error resetting progress file: {e}")

def on_select_video_to_split_click():
    global selected_file_to_split
    selected_file_to_split = filedialog.askopenfilename(
        title="Select Video to Split",
        filetypes=(("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.mpeg *.mpg"), ("All files", "*.*"))
    )
    if selected_file_to_split:
        video_path.set(selected_file_to_split)
        video_duration = VideoFileClip(selected_file_to_split).duration
        formatted_duration = str(datetime.timedelta(seconds=int(video_duration)))
        duration.set(f"Süre: {formatted_duration}")
    else:
        video_path.set("No video selected.")
        duration.set("")

def on_split_button_click(split_duration_hours):
    if selected_file_to_split:
        output_filename_prefix = simpledialog.askstring("Output Filename Prefix", "Enter the output filename prefix:")
        if output_filename_prefix:
            output_directory = filedialog.askdirectory(title="Select Output Directory")
            if output_directory:
                threading.Thread(target=split_video_into_parts, args=(selected_file_to_split, split_duration_hours, output_filename_prefix, output_directory)).start()
                video_path.set(f"Video split into parts and saved to {output_directory}")
            else:
                video_path.set("Output directory not selected.")
        else:
            video_path.set("Output filename prefix not provided.")
    else:
        video_path.set("No video selected to split.")

def split_video_into_parts(filepath, split_duration_hours, output_filename_prefix, output_directory):
    clip = VideoFileClip(filepath)
    total_duration = clip.duration
    split_duration_seconds = split_duration_hours * 3600
    start_time = 0
    part_num = 1

    start_time_proc = time.time()
    
    def update_split_progress_bar(total_duration):
        while progress_split.get() < 100:
            elapsed_time = time.time() - start_time_proc
            progress_split.set((elapsed_time / total_duration) * 100)
            root.update_idletasks()
            time.sleep(0.5)

    threading.Thread(target=update_split_progress_bar, args=(total_duration,)).start()
    
    while start_time < total_duration:
        end_time = min(start_time + split_duration_seconds, total_duration)
        part_clip = clip.subclip(start_time, end_time)
        output_path = os.path.join(output_directory, f"{output_filename_prefix}_part{part_num}.mp4")
        part_clip.write_videofile(output_path, codec="libx264")
        start_time = end_time
        part_num += 1
        print(f"Completed part {part_num} from {start_time} to {end_time}")
        
    end_time_proc = time.time()
    elapsed_time = end_time_proc - start_time_proc
    split_status.set(f"Splitting completed in {elapsed_time:.2f} seconds.")
    progress_split.set(100)

import yt_dlp as youtube_dl

def on_download_button_click():
    link = youtube_link.get()
    if link:
        download_path = filedialog.askdirectory(title="Select Download Directory")
        if download_path:
            try:
                ydl_opts = {
                    'outtmpl': f'{download_path}/%(title)s.%(ext)s',  # Save the video with its title
                    'format': 'best'  # Download the best quality available
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                download_status.set(f"Downloaded to {download_path}")
            except Exception as e:
                download_status.set(f"Error: {str(e)}")
        else:
            download_status.set("Download directory not selected.")
    else:
        download_status.set("No link provided.")

# Initialize the list of selected files
selected_files = []
selected_file_to_split = ""

# Create the main window
root = CTk()
root.title("Video Merger, Splitter, and Downloader")
root.geometry("600x500")
# Create tabs
tab_control = CTkTabview(root, width=680, height=380)
tab_control.add("Merge Videos")
tab_control.add("Split Video")
tab_control.add("Download Video")
tab_control.pack(expand=1, fill="both")

# Merge tab content
merge_tab = tab_control.tab("Merge Videos")
header_frame = CTkFrame(merge_tab)
header_frame.pack(anchor="nw", padx=10, pady=10)

label_beytepe = CTkLabel(header_frame, text="!  SELAM  !", font=("Helvetica", 16))
label_beytepe.pack(side="left")

num_files = StringVar()
num_files.set("Selected 0 files.")
label_num_files = CTkLabel(merge_tab, textvariable=num_files, font=("Helvetica", 12))
label_num_files.pack(pady=5)

merge_status = StringVar()
merge_status.set("")
label_merge_status = CTkLabel(merge_tab, textvariable=merge_status, font=("Helvetica", 12))
label_merge_status.pack(pady=5)

progress = CTkProgressBar(merge_tab)
progress.pack(pady=10)
progress.set(0)

file_listbox = Listbox(merge_tab, height=10, width=40)  # Boyutları artırarak listbox'ı büyüttük
file_listbox.pack(pady=10)

select_button = CTkButton(merge_tab, text="Select Videos", command=on_select_button_click)
select_button.pack(pady=10)

merge_button = CTkButton(merge_tab, text="Merge Videos", command=on_merge_button_click)
merge_button.pack(pady=10)

reset_button = CTkButton(merge_tab, text="Reset", command=reset_app)
reset_button.pack(pady=5)

reset_json_button = CTkButton(merge_tab, text="Reset JSON", command=reset_progress)
reset_json_button.pack(pady=5)

exit_button = CTkButton(merge_tab, text="Exit", command=exit_app)
exit_button.pack(pady=5)

# Display the last processed file
last_file_label = StringVar()
last_file_label.set(f"En son birleştirilen video: {get_last_file()}")
label_last_file = CTkLabel(merge_tab, textvariable=last_file_label, font=("Helvetica", 12))
label_last_file.pack(pady=5)

# Add a listbox to display merged files
merged_files_label = CTkLabel(merge_tab, text="Birleştirilen videolar:", font=("Helvetica", 12))
merged_files_label.pack(pady=5)
merged_files_listbox = Listbox(merge_tab, height=15, width=60)  # Boyutları artırarak listbox'ı büyüttük
merged_files_listbox.pack(pady=10)

# Split tab content
split_tab = tab_control.tab("Split Video")
video_path = StringVar()
video_path.set("No video selected.")

duration = StringVar()
duration.set("")

label_select_video = CTkLabel(split_tab, text="Select a video to split", font=("Helvetica", 12))
label_select_video.pack(pady=5)

select_video_button = CTkButton(split_tab, text="Select Video", command=on_select_video_to_split_click)
select_video_button.pack(pady=5)

label_video_path = CTkLabel(split_tab, textvariable=video_path, font=("Helvetica", 12))
label_video_path.pack(pady=5)

label_duration = CTkLabel(split_tab, textvariable=duration, font=("Helvetica", 12))
label_duration.pack(pady=5)

split_30_sec_button = CTkButton(split_tab, text="Split Video into 30-second parts", command=lambda: on_split_button_click(1/120))
split_30_sec_button.pack(pady=10)

split_1_hour_button = CTkButton(split_tab, text="Split Video into 1-hour parts", command=lambda: on_split_button_click(1))
split_1_hour_button.pack(pady=10)

split_3_hour_button = CTkButton(split_tab, text="Split Video into 3-hour parts", command=lambda: on_split_button_click(3))
split_3_hour_button.pack(pady=10)

split_status = StringVar()
split_status.set("")
label_split_status = CTkLabel(split_tab, textvariable=split_status, font=("Helvetica", 12))
label_split_status.pack(pady=5)

progress_split = CTkProgressBar(split_tab)
progress_split.pack(pady=10)
progress_split.set(0)

exit_button_split = CTkButton(split_tab, text="Exit", command=exit_app)
exit_button_split.pack(pady=5)

# Download tab content
download_tab = tab_control.tab("Download Video")
label_youtube_link = CTkLabel(download_tab, text="Enter YouTube link:", font=("Helvetica", 12))
label_youtube_link.pack(pady=5)

youtube_link = StringVar()
entry_youtube_link = CTkEntry(download_tab, textvariable=youtube_link, height=15, width=460) 
entry_youtube_link.pack(pady=5)

download_button = CTkButton(download_tab, text="Download Video", command=on_download_button_click)
download_button.pack(pady=10)

download_status = StringVar()
download_status.set("No download yet.")
label_download_status = CTkLabel(download_tab, textvariable=download_status, font=("Helvetica", 12))
label_download_status.pack(pady=5)

exit_button_download = CTkButton(download_tab, text="Exit", command=exit_app)
exit_button_download.pack(pady=5)

root.geometry('600x800')
root.mainloop()
