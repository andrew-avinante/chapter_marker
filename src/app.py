from argparse import ArgumentParser
from src.common.chapter_parser import ChapterParser
from media_lib.utils.event_util import load_queue, send_event
from media_lib.events.services import Services
from media_lib.events.file_upload_event import FileUploadEvent
import os

def create_argument_parser() -> ArgumentParser:
    arg_parser = ArgumentParser("Chapter Marker")

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

    for event in load_queue(host, Services.CHAPTER_SVC, 'mu.chapterSvc'):
        chapter_parser = ChapterParser(start_threshold=event.metadata.episode.start_threshold, end_threshold=event.metadata.episode.end_threshold)
        chapter_parser.insert_chapter_markers(os.path.join(root_dir, event.finished_location), root_dir)
        send_event(FileUploadEvent(event.run_id, Services.VIDEO_UPLOAD_SVC.value, event.metadata, event.finished_location), host)


if __name__ == "__main__":
    main()
