#!/usr/bin/env python
import os
from ricecooker.chefs import SushiChef
from ricecooker.classes import nodes, files, licenses
from ricecooker.config import LOGGER, THUMBNAILS              # Use LOGGER to print messages
from le_utils.constants import exercises
from le_utils.constants.languages import getlang_by_name
from le_utils.constants import licenses as le_licenses
from ricecooker.classes.questions import SingleSelectQuestion
from utils import *

import dropbox
import json
import re

# Run constants
################################################################################
# CHANNEL_ID = "64d440bdac615b549fa160ea341ab743"         # Main channel ID
CHANNEL_ID = "bc1a1352ba4f4324a2efbe4e0ec808f3"         # Test channel ID
CHANNEL_NAME = "TicTacLearn Test Channel"                             # Name of Kolibri channel
CHANNEL_SOURCE_ID = "tictaclearn-test-channel"                              # Unique ID for content source
CHANNEL_DOMAIN = "tictaclearn.com"                         # Who is providing the content
CHANNEL_LANGUAGE = "en"                                     # Language of channel
CHANNEL_DESCRIPTION = None                                  # Description of the channel (optional)
CHANNEL_THUMBNAIL = None                                    # Local path or url to image file (optional)
CONTENT_ARCHIVE_VERSION = 1

# Additional constants
################################################################################
VIDEOS_XLS = os.path.join("files", "videos.xls")
ASSESSMENT_XLS = os.path.join("files", "assessments.xls")
CREDENTIALS = os.path.join("credentials", "credentials.json")
VIDEO_FOLDER = os.path.abspath(os.path.join("chefdata", "videos"))
SHEETS_FOLDER = os.path.abspath(os.path.join("chefdata", "sheets"))
FAILED_LINKS_DIR = os.path.join("chefdata", "failed_links")
FAILED_LINKS_JSON = os.path.join(FAILED_LINKS_DIR, "failed_links.json")
FAILED_IMAGES_JSON = os.path.join(FAILED_LINKS_DIR, "failed_image_links.json")
TTL_MAIN_LOGO = os.path.join("files", "Images", "TTLFinalLogo.jpg")

# The chef subclass
################################################################################
class TicTacLearnChef(SushiChef):
    """
    This class converts content from the content source into the format required by Kolibri,
    then uploads the {channel_name} channel to Kolibri Studio.
    Your command line script should call the `main` method as the entry point,
    which performs the following steps:
      - Parse command line arguments and options (run `./sushichef.py -h` for details)
      - Call the `SushiChef.run` method which in turn calls `pre_run` (optional)
        and then the ricecooker function `uploadchannel` which in turn calls this
        class' `get_channel` method to get channel info, then `construct_channel`
        to build the contentnode tree.
    For more info, see https://ricecooker.readthedocs.io
    """
    channel_info = {
        'CHANNEL_ID': CHANNEL_ID,
        'CHANNEL_SOURCE_DOMAIN': CHANNEL_DOMAIN,
        'CHANNEL_SOURCE_ID': CHANNEL_SOURCE_ID,
        'CHANNEL_TITLE': CHANNEL_NAME,
        'CHANNEL_LANGUAGE': CHANNEL_LANGUAGE,
        'CHANNEL_THUMBNAIL': TTL_MAIN_LOGO,
        'CHANNEL_DESCRIPTION': CHANNEL_DESCRIPTION,
    }
    ASSETS_DIR = os.path.abspath('assets')
    DATA_DIR = os.path.abspath('chefdata')
    DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')
    ARCHIVE_DIR = os.path.join(DOWNLOADS_DIR, 'archive_{}'.format(CONTENT_ARCHIVE_VERSION))
    # Your chef subclass can override/extend the following method:
    # get_channel: to create ChannelNode manually instead of using channel_info
    # pre_run: to perform preliminary tasks, e.g., crawling and scraping website
    # __init__: if need to customize functionality or add command line arguments

    def video_node_from_dropbox(self, video_details, link, token):
        dbx = dropbox.Dropbox(token)

        metadata, res = dbx.sharing_get_shared_link_file(url=link)
        # get relative path to video file
        video_path = os.path.relpath(os.path.join(VIDEO_FOLDER, metadata.name))


        if not os.path.isfile(video_path):
            with open(video_path, 'wb') as f:
                f.write(res.content)
        else:
            LOGGER.info("{} already downloaded. Skipping".format(metadata.name))

        video_file = files.VideoFile(path = video_path)

        video_node = nodes.VideoNode(
            title = video_details["title"],
            source_id = link,
            license = licenses.CC_BYLicense("TicTacLearn"),
            files = [video_file]
        )

        return video_node

    # returns an array of questions
    def create_question(self, question_data):
        question_arr = []

        for id, question_metadata in question_data:
            if question_metadata["question"] is None:
                question_text = question_metadata["question_image"]
            else:
                question_text = question_metadata["question"] if question_metadata["question_image"] == None else question_metadata["question"] + " " +question_metadata["question_image"]

            question = SingleSelectQuestion(
                id = id,
                question = question_text,
                correct_answer = question_metadata["correct_answer"],
                all_answers = question_metadata["all_answers"],
                hints = []
            )
            question_arr.append(question)
        
        return question_arr

    def upload_content(self, data, access_token, channel):
        for language, language_value in data.items():
            # convert to title to apply title case for node titles
            language = language.title()
            language_node = nodes.TopicNode(
                title = language,
                source_id = language,
                author = "TicTacLearn",
                description = '',
                thumbnail = TTL_MAIN_LOGO,
                language = getlang_by_name(language)
            )
            for grade, grade_value in language_value.items():
                grade_node = nodes.TopicNode(
                    title = 'Grade {}'.format(grade),
                    source_id = "{}-{}".format(language, grade),
                    author = "TicTacLearn",
                    description= '',
                    thumbnail = TTL_MAIN_LOGO,
                    language=getlang_by_name(language)
                )
                
                for subject, subject_value in grade_value.items():
                    subject = subject.title()
                    subject_node = nodes.TopicNode(
                        title = subject,
                        source_id = "{}-{}-{}".format(language, grade,subject),
                        author = "TicTacLearn",
                        description= '',
                        thumbnail = TTL_MAIN_LOGO,
                        language=getlang_by_name(language) 
                    )
                    for chapter, chapter_value in subject_value.items():
                        chapter = chapter.title()
                        chapter_node = nodes.TopicNode(
                            title = chapter,
                            source_id = "{}-{}-{}-{}".format(language, grade, subject, chapter),
                            author = "TicTacLearn",
                            description= '',
                            thumbnail = TTL_MAIN_LOGO,
                            language=getlang_by_name(language)
                        )
                        for topic, topic_value in chapter_value.items():
                            topic = topic.title()
                            if topic == "Chapter Assessment":
                                questions = self.create_question(topic_value.items())
                                exercise_node = nodes.ExerciseNode(
                                    source_id = "{}-{}-{}-{}-{}".format(language, grade, subject,chapter, topic),
                                    title = topic,
                                    author = "TicTacLearn",
                                    description = "Chapter Assessment",
                                    language = getlang_by_name(language),
                                    license = licenses.CC_BYLicense("TicTacLearn"),
                                    thumbnail = TTL_MAIN_LOGO,
                                    exercise_data = {
                                        "mastery_model": exercises.M_OF_N,
                                        "m": len(questions),
                                        "n": len(questions),
                                        "randomize": True
                                    },
                                    questions = questions
                                )
                                chapter_node.add_child(exercise_node)
                            else:
                                topic_node = nodes.TopicNode(
                                    title = topic,
                                    source_id = "{}-{}-{}-{}-{}".format(language, grade, subject, chapter, topic),
                                    author = "TicTacLearn",
                                    description= '',
                                    thumbnail = TTL_MAIN_LOGO,
                                    language=getlang_by_name(language)
                                )
                                for content_type, content in topic_value.items():
                                    if content_type == "video":
                                        for link, details in content.items():
                                            try:
                                                video_node = self.video_node_from_dropbox(details, link, access_token)
                                                topic_node.add_child(video_node)
                                            except Exception as e:
                                                print(e)
                                                print("Error getting video from dropbox with link: {}".format(link))
                                                self.add_to_failed(link, details, content_type)
                                                continue
                                    else:
                                        # content type is assessment
                                        questions = self.create_question(content.items())
                                        exercise_node = nodes.ExerciseNode(
                                            source_id = "{}-{}-{}-{}-{}-Assessment".format(language, grade, subject, chapter, topic),
                                            title = "{} Assessment".format(topic),
                                            author = "TicTacLearn",
                                            description = "{} Assessment".format(topic),
                                            license = licenses.CC_BYLicense("TicTacLearn"),
                                            thumbnail = TTL_MAIN_LOGO,
                                            exercise_data = {
                                                "mastery_model": exercises.M_OF_N,
                                                "m": len(questions),
                                                "n": len(questions),
                                                "randomize": True
                                            },
                                            questions = questions
                                        )
                                        topic_node.add_child(exercise_node)

                                chapter_node.add_child(topic_node)
                        subject_node.add_child(chapter_node)
                    grade_node.add_child(subject_node)
                language_node.add_child(grade_node)
            channel.add_child(language_node)
        
        return channel

    def get_file_id(self, url):
        regex = '(?<=\/d\/)(.+)(?=\/)'
        result = re.search(regex, url)
        return result.group(1)

    def add_to_failed(self, link, details, content_type):
        with open(FAILED_LINKS_JSON, encoding = 'utf-8') as f:
            try:
                data = json.loads(f.read())
            except:
                # no data in json file
                print('no data in json file')
                with open(FAILED_LINKS_JSON, 'w', encoding='utf-8') as json_file:
                    dict_failed = {}
                    dict_failed[link] = {}
                    dict_failed[link]["title"] = details["title"]
                    dict_failed[link]["type"] = content_type
                    json.dump(dict_failed, json_file, indent = 4, ensure_ascii=False)
                    return
            
            with open(FAILED_LINKS_JSON, 'w', encoding = 'utf-8') as json_file:
                data[link] = {}
                data[link]["title"] = details["title"]
                data[link]["type"]= content_type
                json.dump(data, json_file, indent=4, ensure_ascii=False)
                return
    

    def construct_channel(self, *args, **kwargs):
        """
        Creates ChannelNode and build topic tree
        Args:
          - args: arguments passed in on the command line
          - kwargs: extra options passed in as key="value" pairs on the command line
            For example, add the command line option   lang="fr"  and the value
            "fr" will be passed along to `construct_channel` as kwargs['lang'].
        Returns: ChannelNode
        """
        """
        Channel structure:
            Language > Grade > Subject > Chapter > Topic Name > Content
        """
        channel = self.get_channel(*args, **kwargs)  # Create ChannelNode from data in self.channel_info

        if os.path.exists(FAILED_LINKS_DIR):
            os.remove(FAILED_LINKS_JSON)
        else:
            os.makedirs(FAILED_LINKS_DIR, exist_ok=True)
        
        if not os.path.exists(VIDEO_FOLDER):
            os.makedirs(VIDEO_FOLDER, exist_ok=True)

        if not os.path.exists(SHEETS_FOLDER):
            os.makedirs(SHEETS_FOLDER, exist_ok=True)
        with open(FAILED_LINKS_JSON, 'w+'):
            pass
        with open(FAILED_IMAGES_JSON, 'w+'):
            pass

        # set up dropbox credentials
        with open(CREDENTIALS, 'r') as myfile:
            credentials_data = myfile.read()
        
        creds = json.loads(credentials_data)
        access_token = creds['dropbox_token']


        data = read_videos_xls(VIDEOS_XLS)
        data = read_assessment_xls(ASSESSMENT_XLS, data)

        channel = self.upload_content(data, access_token, channel)
        

        return channel


# CLI
################################################################################
if __name__ == '__main__':
    # This code runs when sushichef.py is called from the command line
    chef = TicTacLearnChef()
    chef.main()