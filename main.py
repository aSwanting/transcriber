import os
import sys
import itertools
import threading
import time

def list_files(files_path):   
    try:
        files = os.listdir(files_path)
        sys.stdout.write("\rFiles found:\n")
        for file in files:
            sys.stdout.write(file + '\n')
        sys.stdout.write('\n')
    except Exception:
        sys.stdout.write("\rInvalid path\n")

def ascii_loader(stop_event):
    loader = itertools.cycle([
        '|.....', '.|....', '..|...', '...|..', '....|.',
        '.....|', '....|.', '...|..', '..|...', '.|....'
    ])
    sys.stdout.write('\n')  
    while not stop_event.is_set():
        sys.stdout.write('\r' + next(loader))  
        sys.stdout.flush()  
        time.sleep(0.1)  

def long_running_task():
    time.sleep(5)

def main():    

    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||     TRANSCRIBER 3000     ||||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n|||||||||||||||||||||||||||||||||||||||||                          |||||||||||||||||||||||||||||||||||||||")
    sys.stdout.write("\n||||||||||||||||||||||||||||||||||||||||||                          ||||||||||||||||||||||||||||||||||||||")
    
    files_path = input("\n\nDrag and drop a folder to list its contents\n").strip('"')
    
    stop_event = threading.Event()
    loader_thread = threading.Thread(target=ascii_loader, args=(stop_event,))
    loader_thread.start()
    
    long_running_task()
    
    stop_event.set()
    loader_thread.join()

    list_files(files_path)

if __name__ == "__main__":
    main()
