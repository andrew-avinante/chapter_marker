from argparse import ArgumentParser
from src.common.chapter_parser import ChapterParser
from media_lib.utils.event_util import load_queue, send_event, send_error
from media_lib.events.services import Services
from media_lib.events.file_upload_event import FileUploadEvent
from media_lib.utils.logging_util import LoggingUtil
import os
import queue
import threading

LoggingUtil.set_logger_name("Chapter Marker Service")
logger = LoggingUtil.get_logger()

def create_argument_parser() -> ArgumentParser:
    arg_parser = ArgumentParser("Chapter Marker Service")

    arg_parser.add_argument(
        '-kafka_host',
        help='IP address of the kafka host',
        required=True
        )

    arg_parser.add_argument(
        '-root_dir',
        help='Root output directory',
        required=True
        )

    return arg_parser


def main():
    arg_parser = create_argument_parser()
    args = vars(arg_parser.parse_args())

    host = args.get('kafka_host')
    root_dir = args.get('root_dir')
    q = queue.Queue()
    threading.Thread(target=load_queue, args=(q, host, Services.CHAPTER_SVC, 'mu.chapterSvc')).start()
    while True:
        event = q.get()
        try:
            chapter_parser = ChapterParser(start_threshold=event.metadata.episode.start_threshold, end_threshold=event.metadata.episode.end_threshold)
            output_path = chapter_parser.insert_chapter_markers(os.path.join(root_dir, event.finished_location), root_dir)
            send_event(FileUploadEvent(event.run_id, Services.VIDEO_UPLOAD_SVC.value, event.metadata, output_path), host)
        except Exception as e:
            logger.error(f"Failed to add chapters: {str(e)}")
            send_error(e, event, Services.CHAPTER_SVC, host)


if __name__ == "__main__":
    main()
