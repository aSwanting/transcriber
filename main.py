import os
import sys
import itertools
import threading
import time

def list_whisper_supported_files(files_path):
    """
    Lists files with supported extensions and under 25 MB in the specified directory or file.
    Args:
        files_path (str): Path to a file or directory.
    Returns:
        list: List of dictionaries containing file paths and sizes of supported files.
    """
    # List of supported file extensions
    supported_extensions = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"]
    supported_files = []

    try:
        # Check if the provided path is a file or a directory
        if os.path.isfile(files_path):
            files = [files_path]  # Single file
        elif os.path.isdir(files_path):
            # List all files in the directory
            files = [os.path.join(files_path, file) for file in os.listdir(files_path)]

        # Process each file
        for file in files:
            file_extension = os.path.splitext(file)[1].lower()  # Get file extension
            file_size = os.path.getsize(file) / (1024 * 1024)  # Get file size in MB

            # Check if file is of a supported extension and under 25 MB
            if file_extension in supported_extensions and file_size < 25:
                supported_files.append({
                    'file_path': file,
                    'file_size': file_size
                })
    except Exception:
        # Handle errors if the path is invalid
        sys.stdout.write(f"Path error: Not a file or a folder.\n")
        return

    # Display supported files
    if supported_files:
        sys.stdout.write("\nSupported file(s) found:\n")
        # Print table headers
        sys.stdout.write(f"\n{'No.':<5} {'File Path':<60} {'Size (MB)':>10}\n")
        sys.stdout.write('-' * 80 + '\n')
        # Print each file's details
        for i, file in enumerate(supported_files, start=1):
            sys.stdout.write(f"{i:<5} {os.path.basename(file['file_path']):<60} {file['file_size']:>10.2f}\n")
    else:
        sys.stdout.write("No supported files found")
    
    sys.stdout.write("\n")
    return supported_files

def ascii_loader(stop_event):
    """
    Displays a simple ASCII loader animation until the stop event is set.
    Args:
        stop_event (threading.Event): Event used to stop the loader animation.
    """
    # Loader animation frames
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
    Simulates a transcription process by waiting for 5 seconds and generating mock transcriptions.
    """
    time.sleep(5) # Simulate processing time

    # Create output path
    file_name_without_ext = os.path.splitext(os.path.basename(file_path))[0] 
    output_path = os.path.join(output_dir, f"{file_name_without_ext}.txt")

    # Create output directory if not present
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create mock transcription
    with open(output_path, 'w') as file:
        file.write(f"Transcription for {file_name_without_ext}")


    # sys.stdout.write(f"\rTranscription complete, files saved to {output_path}\n")

def main():
    """
    Main function to run the application.
    Handles user input, file listing, and transcription process.
    """
    # Display application header
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||     TRANSCRIBER 3000     ||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||\n")

    while True:
        # Get user input for file or directory path
        files_path = input("\nDrag and drop a folder to see supported files, type 'exit' to close.\nSupported extensions: mp3, mp4, mpeg, mpga, m4a, wav, and webm.\nMaximum file size: 25 MB.\n").strip('"')
        
        if files_path == "exit": 
            # Exit the application
            sys.stdout.write("\rExiting application...\n")
            break

        # List and display supported files
        output_dir = os.getcwd() + "\\transcriptions\\" # Build the output directory path
        supported_files = list_whisper_supported_files(files_path)
        if supported_files:
            transcribe_input = input("Transcribe? (y/n)\n").strip().lower()

            if transcribe_input == 'y': 
                # Start loader animation in a separate thread
                stop_event = threading.Event()
                loader_thread = threading.Thread(target=ascii_loader, args=(stop_event,))
                loader_thread.start()
                
                for file in supported_files:
                    transcription(file['file_path'], output_dir)  # Simulate transcription process

                sys.stdout.write(f"\rProcessing complete, transcription(s) saved to {output_dir}")
                
                stop_event.set()  # Stop the loader animation
                loader_thread.join()

                # Ask if the user wants to transcribe more files
                continue_input = input("\nTranscribe more files? (y/n)\n").strip().lower()
                if continue_input != 'y': 
                    sys.stdout.write("\rExiting application...\n")
                    break

            else:
                sys.stdout.write("\rTranscription cancelled\n")

if __name__ == "__main__":
    main()
