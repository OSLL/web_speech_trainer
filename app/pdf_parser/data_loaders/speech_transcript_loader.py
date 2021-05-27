import os

from app.pdf_parser.data_processors.text_processor import TextProcessor


class SpeechTranscriptLoader:
    def load(self,
             file_path: str,
             extract_dir=None,
             process_text=True,
             splitter: str='\n\n'):
        self.__transcript_path = file_path
        with open(file_path, 'r') as transcript_file:
            self.__transcrpt_text = transcript_file.read()



        self.transcripts_processed_parts_list = []
        self.transcripts_list = self.__transcrpt_text.split(splitter)
        text_processor = TextProcessor()
        part_counter = 0

        for transcript_part in self.transcripts_list:
            if process_text:
                text_processor.process(text=transcript_part)
                self.transcripts_processed_parts_list.append(text_processor.get_processed_text())
                text = text_processor.get_processed_text()
            else:
                text = transcript_part

            if extract_dir is not None:
                if not os.path.exists(extract_dir):
                    os.mkdir(extract_dir)
                with open("{}/{}_transcript_part.txt".format(extract_dir, part_counter), "w") as f:
                    f.write(text)
            part_counter += 1