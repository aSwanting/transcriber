import configparser
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import defaultdict

import openai


def ascii_loader(stop_event, file_name_without_ext):
    """
    Displays an ASCII spinner animation until the stop event is set.

    Parameters:
    stop_event (threading.Event): An event used to signal when to stop the animation.
    """
    loader = itertools.cycle(
        [
            "|.....",
            ".|....",
            "..|...",
            "...|..",
            "....|.",
            ".....|",
            "....|.",
            "...|..",
            "..|...",
            ".|....",
        ]
    )

    # Hide cursor
    sys.stdout.write("\033[?25l")

    # Animate loader
    while not stop_event.is_set():
        sys.stdout.write(f"\r{file_name_without_ext} {next(loader)}")
        sys.stdout.flush()
        time.sleep(0.1)

    # Show cursor
    sys.stdout.write("\033[?25h")


def load_api_key():
    """
    Loads the API key from a configuration file. If the configuration file does not exist or does not contain
    an API key, prompts the user to input and save a new API key.

    The API key is stored in a file named 'config.ini' in the current working directory.
    """
    config_path = os.path.join(os.getcwd(), "config.ini")
    config = configparser.ConfigParser()

    # If the configuration file does not exist, create it and prompt for API key
    if not os.path.exists(config_path):
        save_api_key(config, config_path)

    # Read the configuration file
    config.read(config_path)

    # If 'API_KEY' section is not present, create it and prompt for API key
    if "API_KEY" not in config:
        save_api_key(config, config_path)

    # Retrieve the API key value
    key_value = config["API_KEY"].get("key")

    # If the API key is not found, prompt for it again and save it
    if not key_value:
        save_api_key(config, config_path)
        key_value = config["API_KEY"].get("key")

    return key_value


def save_api_key(config, config_path):
    """
    Prompts the user to input an API key and saves it to the configuration file.

    Parameters:
    config (configparser.ConfigParser): The configuration parser instance.
    config_path (str): The path to the configuration file where the API key will be saved.
    """
    value = input("\nAPI key not found\nInsert API key to continue:\n").strip()

    # Ensure the API key is not empty
    while not value:
        sys.stdout.write("\rInvalid API key, insert valid API to continue:\n")
        value = input().strip()

    # Save the API key in the configuration file
    config["API_KEY"] = {"key": value}
    with open(config_path, "w") as file:
        config.write(file)

    sys.stdout.write("\nAPI key saved\n")


def list_whisper_supported_files(files_path):
    """
    Lists files in the given path that are supported by Whisper. Supported file types and maximum size are defined.

    Parameters:
    files_path (str): The path to a directory or a single file to check for supported files.

    Returns:
    list: A list of dictionaries containing information about each supported file (file path and size).
    """
    supported_extensions = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"]
    supported_files = []

    try:
        # Check if the path is a file or a directory and list files accordingly
        if os.path.isfile(files_path):
            files = [files_path]
        elif os.path.isdir(files_path):
            files = [os.path.join(files_path, file) for file in os.listdir(files_path)]

        # Check each file for its extension and size
        for file in files:
            file_extension = os.path.splitext(file)[1].lower()
            file_size = os.path.getsize(file) / (1024 * 1024)

            if file_extension in supported_extensions:
                supported_files.append({"file_path": file, "file_size": file_size})
    except Exception:
        sys.stdout.write(f"Path error: Not a file or a folder.\n")
        return

    # Display the supported files and their details
    if len(supported_files) > 1:
        sys.stdout.write("\nSupported file(s) found:\n")
        sys.stdout.write(f"\n{'No.':<5} {'File Path':<60} {'Size (MB)':>10}\n")
        sys.stdout.write("-" * 80 + "\n")
        for i, file in enumerate(supported_files, start=1):
            sys.stdout.write(
                f"{i:<5} {os.path.basename(file['file_path']):<60} {file['file_size']:>10.2f}\n"
            )
    elif not supported_files:
        sys.stdout.write("No supported files found")

    sys.stdout.write("\n")
    return supported_files


def parse_chunk_info(file_path):
    """
    Returns the base name and chunk index (if any) for a prepared audio file.
    """
    file_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(file_name)[0]

    if "-chunk_" in file_name_without_ext:
        base_name, chunk_suffix = file_name_without_ext.split("-chunk_")
        return base_name, int(chunk_suffix)

    return file_name_without_ext, None


def get_progress_path(base_name, output_dir):
    return os.path.join(output_dir, f"{base_name}.progress.json")


def load_transcription_progress(base_name, output_dir):
    """
    Loads persisted progress for a transcription base name.
    """
    progress_path = get_progress_path(base_name, output_dir)
    if not os.path.exists(progress_path):
        return {"completed_chunks": [], "finished": False}

    try:
        with open(progress_path, "r", encoding="utf-8") as progress_file:
            data = json.load(progress_file)
    except (json.JSONDecodeError, OSError):
        return {"completed_chunks": [], "finished": False}

    # Ensure required keys exist
    data.setdefault("completed_chunks", [])
    data.setdefault("finished", False)
    return data


def save_transcription_progress(base_name, output_dir, progress):
    """
    Persists progress for a transcription base name.
    """
    progress_path = get_progress_path(base_name, output_dir)
    progress["completed_chunks"] = sorted(set(progress.get("completed_chunks", [])))
    progress.setdefault("finished", False)
    with open(progress_path, "w", encoding="utf-8") as progress_file:
        json.dump(progress, progress_file, indent=2)


def record_transcription_success(base_name, chunk_index, output_dir):
    """
    Updates the persisted progress after a successful transcription.
    """
    progress = load_transcription_progress(base_name, output_dir)
    if chunk_index is None:
        progress["finished"] = True
    else:
        completed = set(progress.get("completed_chunks", []))
        completed.add(chunk_index)
        progress["completed_chunks"] = sorted(completed)
        progress["finished"] = False
    save_transcription_progress(base_name, output_dir, progress)


def mark_transcription_finished(base_name, output_dir):
    progress = load_transcription_progress(base_name, output_dir)
    progress["finished"] = True
    save_transcription_progress(base_name, output_dir, progress)


def cleanup_transcription_progress(base_name, output_dir):
    """
    Removes persisted progress, transcript output, and any prepared audio
    artifacts for the given base name.
    """
    progress_path = get_progress_path(base_name, output_dir)
    if os.path.exists(progress_path):
        try:
            os.remove(progress_path)
        except OSError:
            pass

    transcript_path = os.path.join(output_dir, f"{base_name}.txt")
    if os.path.exists(transcript_path):
        try:
            os.remove(transcript_path)
        except OSError:
            pass

    reduced_root = os.path.join(os.getcwd(), "reduced_files")
    chunk_dir = os.path.join(reduced_root, base_name)
    if os.path.isdir(chunk_dir):
        try:
            shutil.rmtree(chunk_dir)
        except OSError:
            pass

    reduced_file = os.path.join(reduced_root, f"{base_name}.ogg")
    if os.path.exists(reduced_file):
        try:
            os.remove(reduced_file)
        except OSError:
            pass


def prepare_file_for_transcription(file_path):
    """
    Prepares a file for transcription by reducing its size if necessary and chunking it if it's too large.

    Parameters:
    file_path (str): The path to the original file.
    output_dir (str): The directory where the output files will be saved.

    Returns:
    list: A list of file paths that are ready for transcription.
    """

    file_name = os.path.basename(file_path)
    file_name_clean = os.path.splitext(file_name)[0]

    # Create the output directory for reduced files, to be deleted after operation is completed
    output_dir = os.path.join(os.getcwd(), "reduced_files")
    os.makedirs(output_dir, exist_ok=True)

    # Reduce the file size
    reduced_file_path, reduced_file_size, duration = reduce_file(
        file_path, file_name_clean, output_dir
    )

    # If the reduced file is still too large, chunk it
    if reduced_file_size > 25:
        # Chunk the file and return a list of chunk paths
        chunk_file_paths = chunk_file(
            reduced_file_path, file_name_clean, reduced_file_size, duration, output_dir
        )
        return chunk_file_paths
    else:
        # Return a list with the single reduced file path
        return [reduced_file_path]


def reduce_file(file_path, file_name_clean, output_dir):
    """
    Reduce the size of the audio file by converting it to OGG format.

    Parameters:
        file_path (str): Path to the input audio file.

    Returns:
        tuple: A tuple containing the path to the reduced file, its size, and duration.
    """

    output_path = os.path.join(output_dir, file_name_clean + ".ogg")

    # Convert the file to ogg using ffmpeg
    sys.stdout.write("Converting to ogg...\n\n")
    sys.stdout.flush()
    command_ffmpeg = [
        "ffmpeg",
        "-v",
        "quiet",
        "-stats",
        "-y",
        "-i",
        file_path,
        output_path,
    ]

    # Start ffmpeg conversion in subprocess
    process = subprocess.Popen(
        command_ffmpeg, stderr=subprocess.PIPE, text=True, bufsize=1
    )

    # Output ffmpeg progress to command line in real time
    while process.poll() is None:
        sys.stderr.write(f"\033[F\033[2K{process.stderr.readline()}")
        sys.stderr.flush()

    # Wait for process to complete
    process.wait()

    sys.stdout.write("File successfully converted to ogg format.\n")
    sys.stdout.flush()

    # Get new file size
    reduced_file_size = os.path.getsize(output_path) / (
        1024 * 1024
    )  # Convert size to MB

    # Get the duration of the reduced file using ffprobe
    duration = get_duration(output_path)

    return output_path, reduced_file_size, duration


def get_duration(file_path):
    command_ffprobe = [
        "ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(command_ffprobe, capture_output=True, text=True)
    duration = float(result.stdout.strip())

    return duration


def chunk_file(
    reduced_file_path, file_name_clean, reduced_file_size, duration, output_dir
):
    """
    Splits the reduced file into chunks of approximately equal duration.

    Parameters:
    reduced_file_path (str): The path to the reduced file.
    reduced_file_size (float): The size of the reduced file in MB.
    duration (float): The duration of the reduced file in seconds.
    output_dir (str): The directory where the chunks will be saved.

    Returns:
    list: A list of file paths for the chunks.
    """
    # Calculate the chunk count and chunk duration
    chunk_output_dir = os.path.join(output_dir, file_name_clean)

    # Calculate how many chunks are needed
    chunk_count = math.ceil(reduced_file_size / 25)

    # Adjust the chunk duration to ensure that the last chunk includes any remaining duration
    chunk_duration = duration / chunk_count

    # Slightly increase the duration of each chunk by a small fraction
    chunk_duration = round(chunk_duration * 1.001, 2)

    sys.stdout.write(
        f"\nFile size over 25MB ({reduced_file_size:.2f} MB), splitting into {chunk_count} chunks of approximately {chunk_duration} seconds each...\n"
    )

    # Create chunk directory using file name
    os.makedirs(chunk_output_dir, exist_ok=True)

    # Split the file into chunks using ffmpeg
    command_ffmpeg_split = [
        "ffmpeg",
        "-v",
        "quiet",
        "-stats",
        "-y",
        "-i",
        reduced_file_path,
        "-f",
        "segment",
        "-segment_time",
        str(chunk_duration),
        "-c",
        "copy",
        os.path.join(chunk_output_dir, file_name_clean + "-chunk_%03d.ogg"),
    ]

    # Start ffmpeg chunking in subprocess
    process = subprocess.Popen(
        command_ffmpeg_split, stderr=subprocess.PIPE, text=True, bufsize=1
    )

    # Output ffmpeg progress to command line in real time
    while process.poll() is None:
        sys.stderr.write(f"\033[F\033[2K{process.stderr.readline()}")
        sys.stderr.flush()

    # Wait for process to complete
    process.wait()

    sys.stdout.write(f"File successfully split into {chunk_count} chunks.\n\n")
    sys.stdout.flush()

    # Return list of chunk files
    chunk_files = sorted(
        [
            os.path.join(chunk_output_dir, file)
            for file in os.listdir(chunk_output_dir)
        ]
    )

    return chunk_files


def transcription(file_path, output_dir):
    """
    Simulates a transcription process by creating a placeholder transcription file in the output directory.

    Parameters:
    file_path (str): Path to the input audio file.
    output_dir (str): The directory where the transcription output file will be saved.
    """
    # Extract the file name and base name (without extension) from the file path
    file_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(file_name)[0]

    # Initialize variables to track the last transcription segment details
    last_id = 0
    last_timestamp_seconds = 0
    last_text = ""

    # Check if the file is a chunk file
    chunk_index = None

    if "-chunk_" in file_name:
        # Extract the base name for chunk files
        base_name, chunk_suffix = file_name_without_ext.split("-chunk_")
        chunk_index = int(chunk_suffix)
        is_chunk = True
    else:
        base_name = file_name_without_ext
        is_chunk = False

    # Define the path for the transcription output file
    output_path = os.path.join(output_dir, f"{base_name}.txt")

    # Calculate spacing for output status display
    spacing = 72 - len(file_name_without_ext)

    # If the file is a chunk and not the first chunk, read the existing transcription file
    if is_chunk and chunk_index not in (None, 0):
        try:
            with open(output_path, "r", encoding="utf-8") as file:
                content = file.read().rstrip()
        except FileNotFoundError:
            content = ""

        if content:
            lines = content.split("\n")

            # Extract the last transcription segment details from the file
            last_id = int(lines[-3].strip())
            last_timestamp = lines[-2].rsplit("--> ")[1].strip()
            last_timestamp_seconds = srt_time_to_seconds(last_timestamp)
            last_text = lines[-1]

    # Create the output directory if it does not already exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Start the ASCII loader animation in a separate thread
    stop_event = threading.Event()
    loader_thread = threading.Thread(
        target=ascii_loader, args=(stop_event, file_name_without_ext)
    )
    loader_thread.start()

    # Send file to whisper function for transcription
    try:
        transcription_srt = whisper(
            file_path, last_timestamp_seconds, last_id, last_text
        )
    finally:
        # Ensure the loader is always stopped, even on errors
        stop_event.set()
        loader_thread.join()

    # Append the transcription result to the output file or create it if it does not exist
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(transcription_srt + "\n")

    record_transcription_success(base_name, chunk_index, output_dir)

    # Output completion status to the console
    sys.stdout.write(f"\r\033[2K{file_name_without_ext}{'.' * spacing}[DONE]\n")


def whisper(file_path, last_timestamp_seconds, last_id, last_text):
    """
    Transcribes an audio file using the OpenAI Whisper model and formats the transcription into SRT (SubRip Subtitle) format.

    Parameters:
    file_path (str): The path to the audio file that needs to be transcribed.
    last_timestamp_seconds (float): The timestamp in seconds of the last transcription segment from a previous chunk (if applicable).
    last_id (int): The ID of the last transcription segment from a previous chunk (if applicable).
    last_text (str): The text of the last transcription segment from a previous chunk (if applicable).

    Returns:
    str: The transcription formatted in SRT (SubRip Subtitle) format.
    """

    # Open the audio file in binary read mode
    with open(file_path, "rb") as audio_file:
        # Request transcription from OpenAI Whisper API with minimal retry/backoff
        max_retries = 3
        delay_seconds = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                transcription_dict = openai.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                ).to_dict()
                break
            except Exception as e:
                if attempt == max_retries:
                    # Re-raise after last attempt; caller prints the error
                    raise
                err_type = type(e).__name__
                details = getattr(e, "message", "") or str(e)

                if not details and getattr(e, "__cause__", None):
                    details = str(e.__cause__)

                response = getattr(e, "response", None)
                if response is not None:
                    status = getattr(response, "status_code", "unknown")
                    body = getattr(response, "text", "")
                    snippet = (body or "").strip().replace("\n", " ")
                    if len(snippet) > 200:
                        snippet = snippet[:200] + "..."
                    details += f" [status={status}, body={snippet}]"

                sys.stdout.write(
                    f"\n{err_type} contacting OpenAI (attempt {attempt}/{max_retries}): {details or 'No details'}\n"
                    f"Retrying in {int(delay_seconds)}s...\n"
                )
                sys.stdout.flush()
                time.sleep(delay_seconds)
                delay_seconds *= 2
                audio_file.seek(0)

    # Initialize an empty list to collect SRT formatted segments
    srt_output = []

    # Iterate over each segment returned by the transcription API
    for segment in transcription_dict["segments"]:
        # Calculate the new ID for this segment by incrementing the segment's ID and adding the last ID
        id = (segment["id"] + 1) + last_id

        # Convert segment start and end times from seconds to SRT time format, adjusted by the last timestamp
        start = seconds_to_srt_time(segment["start"] + last_timestamp_seconds)
        end = seconds_to_srt_time(segment["end"] + last_timestamp_seconds)

        # Get the text of the segment, ensuring it is stripped of leading and trailing whitespace
        text = segment["text"].strip()

        # Append the formatted SRT segment to the output list
        srt_output.append(f"{id}\n{start} --> {end}\n{text}\n")

    # Join all segments into a single string with double newlines separating segments
    return "\n".join(srt_output)


def seconds_to_srt_time(seconds):
    """
    Convert a time duration from seconds to SRT (SubRip Subtitle) time format.

    The SRT time format is "HH:MM:SS,mmm", where HH is hours, MM is minutes, SS is seconds, and mmm is milliseconds.

    Parameters:
    seconds (float): The time duration in seconds.

    Returns:
    str: The time formatted as "HH:MM:SS,mmm".
    """
    # Calculate hours, minutes, seconds, and milliseconds from the total seconds
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)

    # Format and return the time as an SRT timestamp
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def srt_time_to_seconds(srt_time):
    """
    Convert an SRT (SubRip Subtitle) timestamp to seconds.

    The SRT timestamp format is "HH:MM:SS,SSS", where HH is hours, MM is minutes, SS is seconds, and SSS is milliseconds.

    Parameters:
    srt_time (str): The SRT timestamp to convert, in the format "HH:MM:SS,SSS".

    Returns:
    float: The timestamp converted to seconds.
    """
    # Split the SRT timestamp into hours, minutes, seconds, and milliseconds
    h, m, s = srt_time.split(":")
    s, ms = s.split(",")

    # Convert each component to seconds and milliseconds
    hours = int(h)
    minutes = int(m)
    seconds = int(s)
    milliseconds = int(ms)

    # Calculate and return the total time in seconds
    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    return total_seconds


def cleanup_reduced_files():
    """
    Removes "reduced_files" directory after transcription, if present.
    """
    reduced_files_dir = os.path.join(os.getcwd(), "reduced_files")

    if os.path.exists(reduced_files_dir):
        shutil.rmtree(reduced_files_dir)
        sys.stdout.write("\nTemp audio files removed\n")


def main():
    """
    Main function that handles user interaction, file processing, and transcription operations.
    """
    cleanup_on_exit = True
    try:

        # Print application banner
        sys.stdout.write("\n" + "=" * 50 + "\n")
        sys.stdout.write("TRANSCRIBER 3000")
        sys.stdout.write("\n" + "=" * 50 + "\n")

        # Load or prompt for API key
        api_key = load_api_key()
        openai.api_key = api_key

        while True:
            # Prompt user to input a folder or file path
            files_path = input(
                "\nDrag and drop a folder to see supported files, type 'exit' to close.\nSupported extensions: mp3, mp4, mpeg, mpga, m4a, wav, and webm.\nMaximum file size: 25 MB.\n"
            ).strip('"')

            if files_path == "exit":
                sys.stdout.write("\rExiting application...\n")
                break

            # Define output directory for transcriptions
            output_dir = os.path.join(os.getcwd(), "transcriptions")
            supported_files = list_whisper_supported_files(files_path)
            file_count = len(supported_files)

            if supported_files:
                # Ask user if they want to transcribe the supported files
                transcribe_input = (
                    input(f"Transcribe {file_count} file(s)? (y/n)\n").strip().lower()
                )

                if transcribe_input == "y":
                    sys.stdout.write("\033[FProcessing...\n\n")

                    skip_bases = set()
                    prompted_bases = set()

                    for file in supported_files:
                        base_name = os.path.splitext(os.path.basename(file["file_path"]))[0]

                        if base_name in prompted_bases:
                            continue

                        progress_path = get_progress_path(base_name, output_dir)
                        if not os.path.exists(progress_path):
                            continue

                        progress = load_transcription_progress(base_name, output_dir)
                        if progress.get("finished"):
                            continue

                        completed_chunks = progress.get("completed_chunks", [])

                        sys.stdout.write(f"\nFound unfinished transcription for {base_name}.\n")
                        if completed_chunks:
                            chunks_text = ", ".join(f"{idx:03d}" for idx in completed_chunks)
                            sys.stdout.write(f"Completed chunks recorded so far: {chunks_text}.\n")
                        else:
                            sys.stdout.write(
                                "No completed chunks recorded yet, but partial progress exists.\n"
                            )

                        transcript_path = os.path.join(output_dir, f"{base_name}.txt")
                        if os.path.exists(transcript_path):
                            sys.stdout.write(
                                f"Partial transcript located at {transcript_path}.\n"
                            )

                        sys.stdout.write(
                            "Resume now (r), discard progress and start fresh (d), or skip for now (s)? [r]\n"
                        )
                        sys.stdout.flush()

                        while True:
                            choice = input().strip().lower()
                            if not choice:
                                choice = "r"
                            if choice in {"r", "d", "s"}:
                                break
                            sys.stdout.write("Please enter r, d, or s.\n")
                            sys.stdout.flush()

                        if choice == "d":
                            cleanup_transcription_progress(base_name, output_dir)
                            sys.stdout.write(
                                f"{base_name} progress removed. Starting fresh.\n"
                            )
                            sys.stdout.flush()
                        elif choice == "s":
                            skip_bases.add(base_name)
                            sys.stdout.write(
                                f"{base_name} skipped for now. Resume later from the same file.\n"
                            )
                            sys.stdout.flush()

                        prompted_bases.add(base_name)

                    # List to keep track of all files to be transcribed
                    files_to_transcribe = []

                    # Process each supported file
                    for file in supported_files:
                        file_path = file["file_path"]
                        file_size = file["file_size"]
                        base_name = os.path.splitext(os.path.basename(file_path))[0]

                        if base_name in skip_bases:
                            continue

                        if file_size > 25:
                            # Prepare large files for transcription (reduce and chunk if needed)
                            reduce_input = (
                                input(
                                    f"Audio file is larger than 25 MB, reduce and split if necessary? Original file will not be modified. (y/n)\n"
                                )
                                .strip()
                                .lower()
                            )
                            if reduce_input == "y":
                                sys.stdout.write("\033[FReducing...\n\n")
                                files_to_transcribe.extend(
                                    prepare_file_for_transcription(file_path)
                                )
                            else:
                                sys.stdout.write("\033[FSkipping...\n\n")
                        else:
                            # Add files that do not exceed the size limit
                            files_to_transcribe.append(file_path)

                    # Transcribe all files with resume support
                    if files_to_transcribe:
                        sys.stdout.write("Transcribing...\n\n")
                        counter = 0

                        failed_transcriptions = []
                        progress_cache = {}
                        encountered_chunks = defaultdict(set)
                        aborted_bases = set()
                        failed_bases = set()

                        for file_path in files_to_transcribe:
                            base_name, chunk_index = parse_chunk_info(file_path)
                            progress = progress_cache.get(base_name)
                            if progress is None:
                                progress = load_transcription_progress(base_name, output_dir)
                                progress_cache[base_name] = progress

                            if base_name in aborted_bases:
                                continue

                            if chunk_index is not None:
                                encountered_chunks[base_name].add(chunk_index)

                                if progress.get("finished"):
                                    sys.stdout.write(
                                        f"\n{base_name} already fully transcribed. Skipping remaining chunks.\n"
                                    )
                                    sys.stdout.flush()
                                    aborted_bases.add(base_name)
                                    continue

                                if chunk_index in progress.get("completed_chunks", []):
                                    sys.stdout.write(
                                        f"\n{base_name}-chunk_{chunk_index:03d} already completed earlier. Skipping...\n"
                                    )
                                    sys.stdout.flush()
                                    continue
                            else:
                                if progress.get("finished"):
                                    sys.stdout.write(
                                        f"\n{base_name} already transcribed. Remove {base_name}.txt if you need to rerun.\n"
                                    )
                                    sys.stdout.flush()
                                    continue

                            try:
                                transcription(file_path, output_dir)
                                counter += 1
                                progress_cache[base_name] = load_transcription_progress(
                                    base_name, output_dir
                                )
                            except Exception as e:
                                failed_name = os.path.basename(file_path)
                                sys.stdout.write(
                                    f"\n{failed_name} interrupted: {e}\n"
                                    "Progress so far is saved. You can retry this chunk later.\n"
                                )
                                sys.stdout.flush()
                                failed_transcriptions.append(
                                    {
                                        "display": failed_name,
                                        "base_name": base_name,
                                        "chunk_index": chunk_index,
                                    }
                                )
                                aborted_bases.add(base_name)
                                failed_bases.add(base_name)

                        if counter:
                            sys.stdout.write(
                                f"\nProcessing complete, {counter} transcription(s) saved to {output_dir}"
                            )
                            sys.stdout.flush()

                        # Mark completed chunked files
                        for base_name, chunks in encountered_chunks.items():
                            if base_name in failed_bases:
                                continue
                            progress = progress_cache.get(base_name) or load_transcription_progress(
                                base_name, output_dir
                            )
                            completed = set(progress.get("completed_chunks", []))
                            if chunks and chunks.issubset(completed) and not progress.get("finished"):
                                mark_transcription_finished(base_name, output_dir)
                                progress_cache[base_name] = load_transcription_progress(
                                    base_name, output_dir
                                )

                        keep_chunks_for_retry = False

                        if failed_transcriptions:
                            sys.stdout.write("\nFiles that need a retry:\n")
                            for entry in failed_transcriptions:
                                label = entry["display"]
                                if entry["chunk_index"] is not None:
                                    label += f" (chunk {entry['chunk_index']:03d})"
                                sys.stdout.write(f"- {label}\n")
                            sys.stdout.write(
                                "These likely failed due to temporary OpenAI connectivity issues.\n"
                            )
                            sys.stdout.flush()

                            if any(
                                item["chunk_index"] is not None for item in failed_transcriptions
                            ):
                                keep_input = (
                                    input(
                                        "\nKeep the converted/chunked audio so you can retry without reprocessing? (y/n)\n"
                                    )
                                    .strip()
                                    .lower()
                                )
                                if keep_input == "y":
                                    keep_chunks_for_retry = True
                                    cleanup_on_exit = False
                                    sys.stdout.write(
                                        "\nChunk audio kept in reduced_files/. Run the same file again to resume before processing other files.\n"
                                    )
                                    sys.stdout.flush()

                        else:
                            sys.stdout.flush()

                        if not keep_chunks_for_retry:
                            cleanup_reduced_files()
                            cleanup_on_exit = True

                    # Ask user if they want to continue
                    continue_input = (
                        input("\nTranscribe more files? (y/n)\n").strip().lower()
                    )
                    if continue_input != "y":
                        break

                    sys.stdout.write("\033[F \n")

                else:
                    sys.stdout.write("\033[FTranscription cancelled\n")

    except KeyboardInterrupt:
        sys.stdout.write("Operation interrupted by user.\n")
        sys.stdout.flush()

    except Exception as e:
        sys.stdout.write(f"Something broke: {e}\n")
        sys.stdout.flush()

    finally:
        sys.stdout.write("Exiting application...\n")
        sys.stdout.flush()
        if cleanup_on_exit:
            cleanup_reduced_files()  # Clean up before exiting


if __name__ == "__main__":
    main()
