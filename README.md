# Whisper Transcription

A simple transcription app using OpenAI's Whisper.

## On first run
App will ask for a valid OpenAI api key and save it to config.ini.

## Output
Outputs a text file in srt format with numbered segments and timestamps.

## Handling files over 25 MB
Wisper's transcription is limited to 25 MB. To handle larger files, this app first converts to .ogg format, and if necessary, splits the file into shorter chunks. These files are temporary and are deleted post transcription, the original audio file remains untouched. This requires the user to have ffmpeg and ffprobe installed. Alternatively ffmpeg and ffprobe can simply be placed in the working directory.

## Timestamps and segments in chunked files
If converting chunked files, the timestamps and segments are offset by reading the last values of the previous chunk, and a single transcription is generated.



