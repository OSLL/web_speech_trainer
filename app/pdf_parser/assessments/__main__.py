import argparse

from app.pdf_parser.assessments.slide_assessment import main as slide_assessment_main
from app.pdf_parser.assessments.train_assessment import main as speech_assessment_main


def parse_args():
    parser = argparse.ArgumentParser(description='Assessment [package] parser')

    subparsers = parser.add_subparsers()

    parser_slide_assessment = subparsers.add_parser('slide_assessment',
                                                      help="Option for compute slide assessment [on word]")
    parser_slide_assessment.add_argument('--slide_text_file',
                                           type=str,
                                           required=True,
                                           action='store',
                                           dest='slide_text_file'
                                           )
    parser_slide_assessment.add_argument('--transcript_part_text_file',
                                           type=str,
                                           required=True,
                                           action='store',
                                           dest='transcript_part_text_file'
                                           )
    parser_slide_assessment.set_defaults(func=slide_assessment_main)

    parser_speech_assessment = subparsers.add_parser('speech_assessment',
                                                      help="Option for compute speech assessment")
    parser_speech_assessment.add_argument('--pdf_path',
                                         type=str,
                                         required=True,
                                         action='store',
                                         dest='pdf_path'
                                         )
    parser_speech_assessment.add_argument('--transcript_path',
                                         type=str,
                                         required=True,
                                         action='store',
                                         dest='transcript_path'
                                         )
    parser_speech_assessment.set_defaults(func=speech_assessment_main)

    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == '__main__':
    main()