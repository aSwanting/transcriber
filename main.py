import configparser
import itertools
import math
import os
import shutil
import subprocess
import sys
import threading
import time


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

    Args:
        file_path (str): Path to the input audio file.

    Returns:
        tuple: A tuple containing the path to the reduced file, its size, and duration.
    """

    output_path = os.path.join(output_dir, file_name_clean + ".ogg")

    # Convert the file to ogg using ffmpeg
    sys.stdout.write("Converting to ogg...\n\n")
    sys.stdout.flush()
    command_ffmpeg = [
        "static_ffmpeg",
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
    sys.stdout.flush()
    command_ffprobe = [
        "static_ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        output_path,
    ]
    result = subprocess.run(command_ffprobe, capture_output=True, text=True)
    duration = float(result.stdout.strip())

    return output_path, reduced_file_size, duration


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
    chunk_output_dir = os.path.join(output_dir, file_name_clean)
    chunk_count = math.ceil(reduced_file_size / 25)
    chunk_duration = round(duration / chunk_count, 2)
    sys.stdout.write(
        f"\nFile size over 25MB ({reduced_file_size:.2f} MB), splitting into {chunk_count} {chunk_duration} second chunks...\n"
    )

    # Create chunk directory using file name
    os.makedirs(chunk_output_dir, exist_ok=True)

    # Split the file into chunks using ffmpeg
    command_ffmpeg_split = [
        "static_ffmpeg",
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
    # subprocess.run(command_ffmpeg_split, check=True)

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
    chunk_files = [
        os.path.join(chunk_output_dir, file) for file in os.listdir(chunk_output_dir)
    ]
    return chunk_files


def transcription(file_path, output_dir):
    """
    Simulates a transcription process by creating a placeholder transcription file in the output directory.

    Parameters:
    file_path (str): Path to the input audio file.
    output_dir (str): The directory where the transcription output file will be saved.
    """

    file_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(file_name)[0]
    output_path = os.path.join(output_dir, f"{file_name_without_ext}.txt")
    spacing = 72 - len(file_name_without_ext)

    # Create output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Start the ASCII loader animation in a separate thread
    stop_event = threading.Event()
    loader_thread = threading.Thread(
        target=ascii_loader, args=(stop_event, file_name_without_ext)
    )
    loader_thread.start()

    # Simulate transcription time, this will be replaced by OpenAI Whisper Speech-to-Text
    time.sleep(2)

    # Stop the ASCII loader animation
    stop_event.set()
    loader_thread.join()

    # Write a placeholder transcription to the output file
    with open(output_path, "w") as file:
        file.write(f"Transcription for {file_name_without_ext}")
    sys.stdout.write(f"\r\033[2K{file_name_without_ext}{'.' * spacing}[DONE]\n")
    return True


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

    try:

        # Print application banner
        sys.stdout.write("\n" + "=" * 50 + "\n")
        sys.stdout.write("TRANSCRIBER 3000")
        sys.stdout.write("\n" + "=" * 50 + "\n")

        # Load or prompt for API key
        load_api_key()

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

                    # List to keep track of all files to be transcribed
                    files_to_transcribe = []

                    # Process each supported file
                    for file in supported_files:
                        file_path = file["file_path"]
                        file_size = file["file_size"]

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

                    # Transcribe all files, to be added
                    if files_to_transcribe:
                        sys.stdout.write("Transcribing...\n\n")
                        counter = 0

                        for file_path in files_to_transcribe:
                            transcription(file_path, output_dir)
                            counter += 1

                        sys.stdout.write(
                            f"\nProcessing complete, {counter} transcription(s) saved to {output_dir}"
                        )

                    # Clean up the temporary reduced files after transcription
                    cleanup_reduced_files()

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
        cleanup_reduced_files()  # Clean up before exiting

    except Exception as e:
        sys.stdout.write(f"something broke: {e}\n")
        sys.stdout.flush()
        cleanup_reduced_files()  # Clean up before exiting

    finally:
        sys.stdout.write("Exiting application...\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
