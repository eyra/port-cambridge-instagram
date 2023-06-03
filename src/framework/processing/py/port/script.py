import itertools
import port.api.props as props
from port.api.commands import (CommandSystemDonate, CommandUIRender)

import pandas as pd
import zipfile
import json
import datetime
from collections import defaultdict
##########################
# TikTok file processing #
##########################

filter_start = datetime.datetime(2021, 1, 1)
filter_end = datetime.datetime(2025, 1, 1)

datetime_format = "%Y-%m-%d %H:%M:%S"

def get_in(data_dict, *key_path):
    for k in key_path:
        data_dict = data_dict.get(k, None)
        if data_dict is None:
            return None
    return data_dict

def get_video_list_data(data):
    return get_in(data, "Activity", "Video Browsing History", "VideoList")

def get_comment_list_data(data):
    return get_in(data, "Comment", "Comments", "CommentsList")

def get_date_filtered_items(items):
    for item in items:
        timestamp =datetime.datetime.strptime(item["Date"], datetime_format)
        if timestamp < filter_start or timestamp > filter_end:
            continue
        yield (timestamp, item)

def get_count_by_date_key(timestamps, key_func):
    """ Returns a list of tuples of the form (key, count)

    The key is determined by the key_func, which takes a datetime object and
    returns an object suitable for sorting and usage as a dictionary key.

    The returned list is sorted by key.
    """
    item_count = defaultdict(int)
    for timestamp in timestamps:
        item_count[key_func(timestamp)] += 1
    return sorted(item_count.items())

def get_all_first(items):
    return (i[0] for i in items)

def hourly_key(date):
    return date.strftime("%Y-%m-%d %H" )

def daily_key(date):
    return date.strftime("%Y-%m-%d")

def get_sessions(timestamps):
    """ Returns a list of tuples of the form (start, end, duration)

    The start and end are datetime objects, and the duration is a timedelta
    object.
    """
    timestamps = list(sorted(timestamps))
    if len(timestamps) == 0:
        return []
    if len(timestamps) == 1:
        return [(timestamps[0], timestamps[0], datetime.timedelta(0))]

    sessions = []
    start = timestamps[0]
    end = timestamps[0]
    for prev, cur in zip(timestamps, timestamps[1:]):
        if cur - prev > datetime.timedelta(hours=1):
            sessions.append((start, end, end-start))
            start = cur
        end = cur
    sessions.append((start, end, end-start))
    return sessions

def get_json_data(zip_file):
    with zipfile.ZipFile(zip_file, "r") as zip:
        for name in zip.namelist():
            if not name.endswith(".json"):
                continue
            with zip.open(name) as json_file:
                yield json.load(json_file)


def extract_tiktok_data(zip_file):
    for data in get_json_data(zip_file):
        videos = list(get_all_first(get_date_filtered_items(get_video_list_data(data))))
        video_counts=  get_count_by_date_key(videos, hourly_key)
        table_title = props.Translatable({
            "en": "TikTok video browsing history",
            "nl": "TikTok video geschiedenis"
        })
        print(video_counts)
        data_frame = pd.DataFrame(video_counts, columns=["Hour", "View Count"])
        return [props.PropsUIPromptConsentFormTable("tiktok_video_counts", table_title, data_frame)]


        # comment_list_dates = list(get_all_first(get_date_filtered_items(get_comment_list_data(data))))
        # sessions = get_sessions(itertools.chain(video_dates, comment_list_dates))
        # yield sessions

# data = json.load(open(sys.argv[1]))

# from pprint import pprint
# video_dates = list(get_all_first(get_date_filtered_items(get_video_list_data(data))))
# pprint(get_count_by_date_key(video_dates, hourly_key))
# pprint(get_count_by_date_key(video_dates, daily_key))
# print("#"*80)
# comment_list_dates = list(get_all_first(get_date_filtered_items(get_comment_list_data(data))))
# pprint(get_count_by_date_key(comment_list_dates, hourly_key))
# pprint(get_count_by_date_key(comment_list_dates, daily_key))

# sessions = get_sessions(itertools.chain(video_dates, comment_list_dates))
# pprint(sessions)


######################
# Data donation flow #
######################

def process_tiktok(sessionId):
    progress = 0
    platform = "TikTok"
    meta_data = []
    data = None
    while True:
        promptFile = prompt_file(platform, "application/zip, text/plain")
        fileResult = yield render_donation_page(platform, promptFile, progress)
        if fileResult.__type__ != 'PayloadString':
            meta_data.append(("debug", f"{platform}: skip to next step"))
            break

        meta_data.append(("debug", f"{platform}: extracting file"))
        extractionResult = extract_tiktok_data(fileResult.value)
        if extractionResult != 'invalid':
            meta_data.append(("debug", f"{platform}: extraction successful, go to consent form"))
            data = extractionResult
            break

        meta_data.append(("debug", f"{platform}: prompt confirmation to retry file selection"))
        retry_result = yield render_donation_page(platform, retry_confirmation(platform), progress)
        if retry_result.__type__ == 'PayloadTrue':
            meta_data.append(("debug", f"{platform}: skip due to invalid file"))
            continue

        meta_data.append(("debug", f"{platform}: retry prompt file"))
        break
    if data:
        meta_data.append(("debug", f"{platform}: prompt consent"))
        consent_result = yield render_donation_page(platform, props.PropsUIPromptConsentForm(data, []), progress)

        if consent_result.__type__ == "PayloadJSON":
            meta_data.append(("debug", f"{platform}: donate consent data"))
            yield donate(f"{sessionId}-{platform}", consent_result.value)


def process(sessionId):
    progress = 0
    yield donate(f"{sessionId}-tracking", '[{ "message": "user entered script" }]')
    yield from process_tiktok(sessionId)

    # subflows = len(platforms)
    # steps = 2
    # step_percentage = (100/subflows)/steps

    # # progress in %
    # progress = 0

    # for index, platform in enumerate(platforms):
    #     meta_data = []
    #     meta_data.append(("debug", f"{platform}: start"))

    #     # STEP 1: select the file
    #     progress += step_percentage
    #     data = None
    #     while True:
    #         meta_data.append(("debug", f"{platform}: prompt file"))
    #         promptFile = prompt_file(platform, "application/zip, text/plain")
    #         fileResult = yield render_donation_page(platform, promptFile, progress)
    #         if fileResult.__type__ == 'PayloadString':
    #             meta_data.append(("debug", f"{platform}: extracting file"))
    #             extractionResult = doSomethingWithTheFile(platform, fileResult.value)
    #             if extractionResult != 'invalid':
    #                 meta_data.append(("debug", f"{platform}: extraction successful, go to consent form"))
    #                 data = extractionResult
    #                 break
    #             else:
    #                 meta_data.append(("debug", f"{platform}: prompt confirmation to retry file selection"))
    #                 retry_result = yield render_donation_page(platform, retry_confirmation(platform), progress)
    #                 if retry_result.__type__ == 'PayloadTrue':
    #                     meta_data.append(("debug", f"{platform}: skip due to invalid file"))
    #                     continue
    #                 else:
    #                     meta_data.append(("debug", f"{platform}: retry prompt file"))
    #                     break
    #         else:
    #             meta_data.append(("debug", f"{platform}: skip to next step"))
    #             break

    #     # STEP 2: ask for consent
    #     progress += step_percentage
    #     if data is not None:
    #         meta_data.append(("debug", f"{platform}: prompt consent"))
    #         prompt = prompt_consent(platform, data, meta_data)
    #         consent_result = yield render_donation_page(platform, prompt, progress)
    #         if consent_result.__type__ == "PayloadJSON":
    #             meta_data.append(("debug", f"{platform}: donate consent data"))
    #             yield donate(f"{sessionId}-{platform}", consent_result.value)

    yield render_end_page()


def render_end_page():
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)


def render_donation_page(platform, body, progress):
    header = props.PropsUIHeader(props.Translatable({
        "en": platform,
        "nl": platform
    }))

    footer = props.PropsUIFooter(progress)
    page = props.PropsUIPageDonation(platform, header, body, footer)
    return CommandUIRender(page)


def retry_confirmation(platform):
    text = props.Translatable({
        "en": f"Unfortunately, we cannot process your {platform} file. Continue, if you are sure that you selected the right file. Try again to select a different file.",
        "nl": f"Helaas, kunnen we uw {platform} bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
    })
    ok = props.Translatable({
        "en": "Try again",
        "nl": "Probeer opnieuw"
    })
    cancel = props.Translatable({
        "en": "Continue",
        "nl": "Verder"
    })
    return props.PropsUIPromptConfirm(text, ok, cancel)


def prompt_file(platform, extensions):
    description = props.Translatable({
        "en": f"Please follow the download instructions and choose the file that you stored on your device. Click “Skip” at the right bottom, if you do not have a {platform} file. ",
        "nl": f"Volg de download instructies en kies het bestand dat u opgeslagen heeft op uw apparaat. Als u geen {platform} bestand heeft klik dan op “Overslaan” rechts onder."
    })

    return props.PropsUIPromptFileInput(description, extensions)


def doSomethingWithTheFile(platform, filename):
    return extract_zip_contents(filename)


def extract_zip_contents(filename):
    names = []
    try:
        file = zipfile.ZipFile(filename)
        data = []
        for name in file.namelist():
            names.append(name)
            info = file.getinfo(name)
            data.append((name, info.compress_size, info.file_size))
        return data
    except zipfile.error:
        return "invalid"


def prompt_consent(id, data, meta_data):

    table_title = props.Translatable({
        "en": "Zip file contents",
        "nl": "Inhoud zip bestand"
    })

    log_title = props.Translatable({
        "en": "Log messages",
        "nl": "Log berichten"
    })

    data_frame = pd.DataFrame(data, columns=["filename", "compressed size", "size"])
    table = props.PropsUIPromptConsentFormTable("zip_content", table_title, data_frame)
    meta_frame = pd.DataFrame(meta_data, columns=["type", "message"])
    meta_table = props.PropsUIPromptConsentFormTable("log_messages", log_title, meta_frame)
    return props.PropsUIPromptConsentForm([table], [meta_table])


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)
