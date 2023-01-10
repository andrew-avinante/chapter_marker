import ffmpeg
import re
from threading import Thread
from subprocess import Popen
from media_lib.utils.logging_util import LoggingUtil
import os

SCREEN = "SCREEN"
AUDIO = "AUDIO"

logger = LoggingUtil.get_logger()

REGEX = {
    SCREEN: {
        "start": r"(?<=black_start:)[0-9]*\.?[0-9]*",
        "end": r"(?<=black_end:)[0-9]*\.?[0-9]*"
    },
    AUDIO: {
        "start": r"(?<=silence_start: )[0-9]*\.?[0-9]*",
        "end": r"(?<=silence_end: )[0-9]*\.[0-9]*"
    }
}

class ChapterParser():
    def __init__(self, start_threshold: int = 60, end_threshold: int = 60):
        self.start_threshold = start_threshold
        self.end_threshold = end_threshold

    def _extract_times(self, process: Popen, mode: str, result: list = []):
        stack = []

        while True:
            line = process.stderr.readline()
            if not line:
                break
            decoded_line = line.decode('utf-8')
            matches = re.findall(REGEX[mode]['start'], decoded_line)

            if len(matches):
                if mode == SCREEN:
                    result.append(round((float(matches[0]) + float(re.findall(REGEX[mode]['end'], decoded_line)[0])) / 2))
                else:
                    stack.append(float(matches[0]))
            elif len(matches := re.findall(REGEX[mode]['end'], decoded_line)):
                result.append(round((stack.pop() + float(matches[0])) / 2))

        return result

    def _get_closest_val(self, input_value: int, input_list: list):
        difference = lambda input_list : abs(input_list - input_value)
        res = min(input_list, key=difference)
        
        return res

    def seconds_to_timestamp(self, time: int):
        return f"{time // 3600:02}:{time // 60:02}:{time % 60}"

    def detect_null_av(self, file: str, mode: str, result: list = [], **kwargs: dict):
        stream = ffmpeg.input(file)
        stream = ffmpeg.filter(stream, filter_name='blackdetect' if mode == SCREEN else 'silencedetect', **kwargs)
        stream = ffmpeg.output(stream, "/dev/null", format="rawvideo" if mode == SCREEN else 'null')
        return self._extract_times(ffmpeg.run_async(stream, overwrite_output=True, pipe_stderr=True), mode, result)

    def get_black_spots(self, file: str, result: list):
        return self.detect_null_av(file, SCREEN, result, d=0.1, pix_th=0.1)

    def get_audioless_spots(self, file: str, result: list):
        return self.detect_null_av(file, AUDIO, result, n="-50dB", d=0.001)

    def get_commercial_blocks(self, file: str):
        logger.info("RETRIEVING COMMERCIAL BLOCKS")
        duration = float(ffmpeg.probe(file).get('format', {}).get('duration', 0))

        black_spots = []
        silence_spots = []

        t1 = Thread(target=self.get_black_spots, args=(file, black_spots))
        t2 = Thread(target=self.get_audioless_spots, args=(file, silence_spots))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        blocks = [{
                        'startTime': 0,
                        'title': f'Commercial Block 1'
                    }]

        count = 2
        for time in black_spots:
            distance = abs(time - self._get_closest_val(time, silence_spots))
            if distance <= 1 and time > self.start_threshold and duration - time > self.end_threshold:
                blocks.append(
                    {
                        'startTime': time,
                        'title': f'Commercial Block {count}'
                    }
                )

                count += 1
        logger.info("RETRIEVED")
        return duration, blocks


    def insert_chapter_markers(self, file: str, root_dir: str):
        duration, chapters = self.get_commercial_blocks(file)
        text = ""
        chapter_count = len(chapters)

        logger.info("LOADING METADATA...")

        stream = ffmpeg.input(file)
        stream = ffmpeg.output(stream, 'FFMETADATAFILE', format='ffmetadata')
        ffmpeg.run(stream, overwrite_output=True, quiet=True)

        with open("FFMETADATAFILE", "a") as f:

            for i in range(chapter_count):
                chapter = chapters[i]
                title = chapter['title']
                start = chapter['startTime']
                end = chapters[i+1]['startTime'] - 1 if i < chapter_count - 1 else round(duration)
                text += f"""
[CHAPTER]
TIMEBASE=1/1000
START={start * 1000}
END={end * 1000}
title={title}
"""
                logger.info(f"Added commercial block at {self.seconds_to_timestamp(start)}") 
            f.write(text)
            f.close()
        
        logger.info("APPLYING METADATA...")
        stream = ffmpeg.input(file)
        stream = ffmpeg.output(stream, os.path.join(root_dir, 'Chapters', f"{file.rsplit('/', 1)[1]}"), i = 'FFMETADATAFILE', map_metadata = 1, codec = 'copy')
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
