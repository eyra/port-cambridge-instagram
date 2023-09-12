"""
- test file type error
- test data not found error
- grouping by hour
    - multiple columns


"""

import json
import io
from pathlib import Path
from dataclasses import dataclass
from inspect import cleandoc
import pandas as pd
from pandas.testing import assert_frame_equal
from port.api import commands
from port import script


class FakeZip:
    def __init__(self, files):
        self._files = files

    def namelist(self):
        return self._files.keys()

    def open(self, name):
        data = self._files[name]
        f = io.StringIO()
        json.dump(data, f)
        f.seek(0)
        return f


def assert_frame_str_equal(df1, df2):
    assert cleandoc(df1) == str(df2)


def test_summary_table():
    data = FakeZip(
        {
            "followers_and_following/followers_1.json": {"string_list_data": [{}, {}]},
            "followers_and_following/followers_2.json": {"string_list_data": [{}]},
            # Some example files have an additional list
            "followers_and_following/followers_3.json": [{"string_list_data": [{}]}],
            "followers_and_following/following.json": {
                "relationships_following": [
                    {},
                    {},
                    {},
                    {},
                ]
            },
            "content/posts_1.json": [
                {},
                {},
                {},
                {},
                {},
            ],
            "comments/post_comments.json": {"comments_media_comments": [{}]},
            "ads_and_topics/videos_watched.json": {
                "impressions_history_videos_watched": [{}, {}]
            },
            "ads_and_topics/posts_viewed.json": {
                "impressions_history_posts_seen": [{}, {}]
            },
            "ads_and_topics/ads_viewed.json": {
                "impressions_history_ads_seen": [{}, {}]
            },
            "messages/inbox/some_person/message_1.json": {
                "participants": [{"name": "Some"}, {"name": "Me"}],
                "messages": [
                    {"sender_name": "Me"},
                    {"sender_name": "Some"},
                    {"sender_name": "Me"},
                ],
            },
            "messages/inbox/some_person/message_2.json": {
                "participants": [{"name": "Me"}],
                "messages": [
                    {"sender_name": "Me"},
                    {"sender_name": "Me"},
                ],
            },
        }
    )
    result = script.extract_summary_data(data)
    assert "instagram_summary" == result.id
    assert "Summary information" == result.title.translations["en"]

    reference = """
             Description  Number
    0          Followers       4
    1          Following       4
    2              Posts       5
    3    Comments posted       1
    4     Videos watched       2
    5       Posts viewed       2
    6      Messages sent       4
    7  Messages received       1
    8         Ads viewed       2
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)


video_posts = {
    "content/posts_1.json": [
        {"media": [{"creation_timestamp": 1678743234}]},
        {"media": [{"creation_timestamp": 1678752349}]},
    ],
    "content/igtv_videos.json": {
        "ig_igtv_media": [
            {"media": [{"creation_timestamp": 1678743235}]},
            {"media": [{"creation_timestamp": 1678752319}]},
            {"media": [{"creation_timestamp": 1678769988}]},
        ]
    },
    "content/reels.json": {
        "ig_reels_media": [
            {"media": [{"creation_timestamp": 1678752377}]},
            {"media": [{"creation_timestamp": 1678793248}]},
        ]
    },
    "content/stories.json": {
        "ig_stories": [
            {"creation_timestamp": 1678743234},
        ]
    },
}


def test_video_posts_table():
    data = FakeZip(video_posts)
    result = script.extract_video_posts(data)
    assert "instagram_video_posts" == result.id
    assert "Posts" == result.title.translations["en"]

    reference = """
             Date Timeslot  Videos  Stories
    0  2023-03-13    22-23       2        1
    1  2023-03-14      1-2       3        0
    2  2023-03-14      5-6       1        0
    3  2023-03-14    12-13       1        0
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)


comments_data = {
    "comments/post_comments.json": {
        "comments_media_comments": [
            {"string_map_data": {"Time": {"timestamp": 1678743234}}},
            {"string_map_data": {"Time": {"timestamp": 1678752349}}},
        ]
    },
    "likes/liked_comments.json": {
        "likes_comment_likes": [{"string_list_data": [{"timestamp": 1678743446}]}],
    },
    "likes/liked_posts.json": {
        "likes_media_likes": [{"string_list_data": [{"timestamp": 1678743446}]}]
    },
}


def test_comments_and_likes_table():
    data = FakeZip(comments_data)
    result = script.extract_comments_and_likes(data)
    assert "instagram_comments_and_likes" == result.id
    assert "Comments and likes" == result.title.translations["en"]

    reference = """
             Date Timeslot  Comments  Likes
    0  2023-03-13    22-23         1      2
    1  2023-03-14      1-2         1      0
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)


def test_viewed_table():
    data = FakeZip(
        {
            "ads_and_topics/videos_watched.json": {
                "impressions_history_videos_watched": [
                    {"string_map_data": {"Time": {"timestamp": 1678741258}}},
                    {"string_map_data": {"Time": {"timestamp": 1678741258}}},
                ]
            },
            "ads_and_topics/posts_viewed.json": {
                "impressions_history_posts_seen": [
                    {"string_map_data": {"Time": {"timestamp": 1678741258}}},
                    {"string_map_data": {"Time": {"timestamp": 1678798788}}},
                ]
            },
        },
    )
    result = script.extract_viewed(data)
    assert "instagram_viewed" == result.id
    assert "Viewed" == result.title.translations["en"]

    reference = """
             Date Timeslot  Videos  Posts
    0  2023-03-13    22-23       2      1
    1  2023-03-14    13-14       0      1
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)


def test_session_info_table():
    data = FakeZip({**video_posts, **comments_data})
    result = script.extract_session_info(data)
    assert "instagram_session_info" == result.id
    assert "Session information" == result.title.translations["en"]

    reference = """
                  Start  Duration (in minutes)
    0  2023-03-13 22:33                   3.53
    1  2023-03-14 01:05                   0.97
    2  2023-03-14 05:59                   0.00
    3  2023-03-14 12:27                   0.00
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)


def test_direct_message_activity_table():
    data = FakeZip(
        {
            "messages/inbox/some_person/message_1.json": {
                "participants": [{"name": "Some"}, {"name": "Me"}],
                "messages": [
                    {
                        "sender_name": "Me",
                        "timestamp_ms": 1677493123321,
                    },
                    {
                        "sender_name": "Some",
                        "timestamp_ms": 1677493127655,
                    },
                    {
                        "sender_name": "Me",
                        "timestamp_ms": 1677493187671,
                    },
                ],
            },
            "messages/inbox/some_other/message_1.json": {
                "participants": [{"name": "Other"}, {"name": "Me"}],
                "messages": [
                    {
                        "sender_name": "Other",
                        "timestamp_ms": 1677493295441,
                    },
                    {
                        "sender_name": "Me",
                        "timestamp_ms": 1677493299999,
                    },
                    {
                        "sender_name": "Other",
                        "timestamp_ms": 1677493299999,
                    },
                ],
            },
        },
    )
    result = script.extract_direct_message_activity(data)
    assert "instagram_direct_message_activity" == result.id
    assert "Direct message activity" == result.title.translations["en"]

    reference = """
       Anonymous ID              Sent
    0             0  2023-02-27 11:18
    1             1  2023-02-27 11:18
    2             0  2023-02-27 11:19
    3             2  2023-02-27 11:21
    4             0  2023-02-27 11:21
    5             2  2023-02-27 11:21
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)

def test_empty_direct_message_activity_table():
    data = FakeZip(
        {
            "messages/inbox/some_person/message_1.json": {
                "participants": [{"name": "Some"}, {"name": "Me"}],
                "messages": [
                ],
            },
            "messages/inbox/some_other/message_1.json": {
                "participants": [{"name": "Other"}, {"name": "Me"}],
                "messages": [
                ],
            },
        },
    )
    result = script.extract_direct_message_activity(data)
    assert "instagram_direct_message_activity" == result.id
    assert "Direct message activity" == result.title.translations["en"]

    reference = """
    Empty DataFrame
    Columns: [Anonymous ID, Sent]
    Index: []
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)

def test_comment_activity_table():
    data = FakeZip(
        {
            "comments/post_comments.json": {
                "comments_media_comments": [
                    {"string_map_data": {"Time": {"timestamp": 1678743434}}},
                    {"string_map_data": {"Time": {"timestamp": 1678743478}}},
                    {"string_map_data": {"Time": {"timestamp": 1678747777}}},
                    {"string_map_data": {"Time": {"timestamp": 1678749999}}},
                    {"string_map_data": {"Time": {"timestamp": 1678999999}}},
                ]
            },
        },
    )
    result = script.extract_comment_activity(data)
    assert "instagram_comment_activity" == result.id
    assert "Comment activity" == result.title.translations["en"]

    reference = """
                 Posted
    0  2023-03-13 22:37
    1  2023-03-13 22:37
    2  2023-03-13 23:49
    3  2023-03-14 00:26
    4  2023-03-16 21:53
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)


def test_posts_liked_table():
    data = FakeZip(
        {
            "likes/liked_posts.json": {
                "likes_media_likes": [
                    {
                        "string_list_data": [
                            {
                                "timestamp": 1678743446,
                                "href": "https://example.org/test1",
                            }
                        ]
                    },
                    {
                        "string_list_data": [
                            {
                                "timestamp": 1678743467,
                                "href": "https://example.org/test2",
                            }
                        ]
                    },
                    {
                        "string_list_data": [
                            {
                                "timestamp": 1678747777,
                                "href": "https://example.org/test3",
                            }
                        ]
                    },
                ]
            },
        },
    )
    result = script.extract_posts_liked(data)
    assert "instagram_posts_liked" == result.id
    assert "Posts Liked" == result.title.translations["en"]

    reference = """
                  Liked                       Link
    0  2023-03-13 22:37  https://example.org/test1
    1  2023-03-13 22:37  https://example.org/test2
    2  2023-03-13 23:49  https://example.org/test3
    """
    print(result.data_frame)
    assert_frame_str_equal(reference, result.data_frame)
