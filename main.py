import os
import sys
import itertools
import threading
import time

def list_whisper_supported_files(files_path):
        
        supported_extensions = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"]
        supported_files = []

        try:
            if os.path.isfile(files_path):
                files = [files_path]
            elif os.path.isdir(files_path):
                files = [os.path.join(files_path, file) for file in os.listdir(files_path)]

            for file in files:
                file_extension = os.path.splitext(file)[1].lower()
                file_size = os.path.getsize(file)/(1024 * 1024)

                if file_extension in supported_extensions and file_size < 25 :
                    supported_files.append({
                        'file_path': file,
                        'file_size': file_size
                    })
        except Exception:
            sys.stdout.write(f"Path error: Not a file or a folder.\n")
            return

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
    loader = itertools.cycle([
        '|.....', '.|....', '..|...', '...|..', '....|.',
        '.....|', '....|.', '...|..', '..|...', '.|....'
    ])
    sys.stdout.write('\n')  
    while not stop_event.is_set():
        sys.stdout.write(f"\r {next(loader)} ")  
        sys.stdout.flush()  
        time.sleep(0.1)  

def transcription():
    time.sleep(5)
    output_path = os.getcwd()+"\\transcriptions\\"
    sys.stdout.write(f"\rTranscription complete, files saved to {output_path}\n")


def main():
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||     TRANSCRIBER 3000     ||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||\n")

    while True:

        files_path = input("\nDrag and drop a folder to see supported files, type 'exit' to close.\nSupported extensions: mp3, mp4, mpeg, mpga, m4a, wav, and webm.\nMaximum file size: 25 MB.\n").strip('"')
        
        if files_path == "exit": 
            sys.stdout.write("\rExiting application...\n")
            break

        if list_whisper_supported_files(files_path):
            transcribe_input = input("Transcribe? (y/n)\n").strip().lower()

            if transcribe_input == 'y': 
                stop_event = threading.Event()
                loader_thread = threading.Thread(target=ascii_loader, args=(stop_event,))
                loader_thread.start()
                
                transcription()
                
                stop_event.set()
                loader_thread.join()

                continue_input = input("Transcribe more files? (y/n)\n").strip().lower()
                if continue_input != 'y': 
                    sys.stdout.write("\rExiting application...\n")
                    break

            else:
                sys.stdout.write("\rTranscription cancelled\n")
        

if __name__ == "__main__":
    main()
