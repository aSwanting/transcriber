import os
import sys
import itertools
import threading
import time
import configparser

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
    if 'API_KEY' not in config:
        save_api_key(config, config_path)

    # Retrieve the API key value
    key_value = config['API_KEY'].get('key')

    # If the API key is not found, prompt for it again and save it
    if not key_value:
        save_api_key(config, config_path)
        key_value = config['API_KEY'].get('key')


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
    config['API_KEY'] = {'key': value}
    with open(config_path, 'w') as file:
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

            if file_extension in supported_extensions and file_size < 25:
                supported_files.append({
                    'file_path': file,
                    'file_size': file_size
                })
    except Exception:
        sys.stdout.write(f"Path error: Not a file or a folder.\n")
        return

    # Display the supported files and their details
    if supported_files:
        sys.stdout.write("\nSupported file(s) found:\n")
        sys.stdout.write(f"\n{'No.':<5} {'File Path':<60} {'Size (MB)':>10}\n")
        sys.stdout.write('-' * 80 + '\n')
        for i, file in enumerate(supported_files, start=1):
            sys.stdout.write(f"{i:<5} {os.path.basename(file['file_path']):<60} {file['file_size']:>10.2f}\n")
    else:
        sys.stdout.write("No supported files found")
    
    sys.stdout.write("\n")
    return supported_files


def ascii_loader(stop_event):
    """
    Displays an ASCII spinner animation until the stop event is set.

    Parameters:
    stop_event (threading.Event): An event used to signal when to stop the animation.
    """
    loader = itertools.cycle([
        '|.....', '.|....', '..|...', '...|..', '....|.',
        '.....|', '....|.', '...|..', '..|...', '.|....'
    ])
    sys.stdout.write('\n')  
    
    while not stop_event.is_set():
        sys.stdout.write(f"\r {next(loader)} ")  
        sys.stdout.flush()  
        time.sleep(0.1)  


def transcription(file_path, output_dir):
    """
    Simulates a transcription process by creating a placeholder transcription file in the output directory.

    Parameters:
    file_path (str): The path to the file being transcribed.
    output_dir (str): The directory where the transcription output file will be saved.
    """
    time.sleep(5)

    file_name_without_ext = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{file_name_without_ext}.txt")

    # Create output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Write a placeholder transcription to the output file
    with open(output_path, 'w') as file:
        file.write(f"Transcription for {file_name_without_ext}")


def main():
    """
    Main function that handles user interaction, file processing, and transcription operations.
    """
    # Print application banner
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||     TRANSCRIBER 3000     ||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||\n")

    # Load or prompt for API key
    load_api_key()

    while True:
        # Prompt user to input a folder or file path
        files_path = input("\nDrag and drop a folder to see supported files, type 'exit' to close.\nSupported extensions: mp3, mp4, mpeg, mpga, m4a, wav, and webm.\nMaximum file size: 25 MB.\n").strip('"')
        
        if files_path == "exit": 
            sys.stdout.write("\rExiting application...\n")
            break

        # Define output directory for transcriptions
        output_dir = os.path.join(os.getcwd(), "transcriptions" )
        supported_files = list_whisper_supported_files(files_path)
        
        if supported_files:
            # Ask user if they want to transcribe the supported files
            transcribe_input = input("Transcribe? (y/n)\n").strip().lower()

            if transcribe_input == 'y': 
                # Start the ASCII loader animation in a separate thread
                stop_event = threading.Event()
                loader_thread = threading.Thread(target=ascii_loader, args=(stop_event,))
                loader_thread.start()
                
                # Process each supported file for transcription
                for file in supported_files:
                    transcription(file['file_path'], output_dir)

                sys.stdout.write(f"\rProcessing complete, transcription(s) saved to {output_dir}")
                
                # Stop the ASCII loader animation
                stop_event.set()
                loader_thread.join()

                # Ask user if they want to continue
                continue_input = input("\nTranscribe more files? (y/n)\n").strip().lower()
                if continue_input != 'y': 
                    sys.stdout.write("\rExiting application...\n")
                    break

            else:
                sys.stdout.write("\rTranscription cancelled\n")

if __name__ == "__main__":
    main()
