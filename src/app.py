from argparse import ArgumentParser
from common.chapter_parser import ChapterParser

def create_argument_parser() -> ArgumentParser:
    arg_parser = ArgumentParser("Chapter Marker")

    arg_parser.add_argument(
        '-start_threshold',
        help='Intro time in seconds',
        required=False,
        default=60
        )
    
    arg_parser.add_argument(
        '-end_threshold',
        help='Credits time in seconds',
        required=False,
        default=60
        )

    arg_parser.add_argument(
        '-i',
        help='Input file',
        required=True
    )

    return arg_parser


def main():
    arg_parser = create_argument_parser()
    args = vars(arg_parser.parse_args())
    chapter_parser = ChapterParser(start_threshold=args.get('start_threshold'), end_threshold=args.get('end_threshold'))
    chapter_parser.insert_chapter_markers(args.get('i'))


if __name__ == "__main__":
    main()
