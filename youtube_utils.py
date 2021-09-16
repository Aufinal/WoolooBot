import youtube_dl


class NoSearchResultsError(Exception):
    pass


ytdl_format_options = {
    "format": "bestaudio/best",
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": "in_playlist",
    "default_search": "ytsearch",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


def to_yt_dict(ytdl_info, processed=True):
    return {
        "title": ytdl_info["title"],
        "duration": ytdl_info["duration"],
        "url": ytdl_info["url"],
        "processed": processed,
    }


def yt_search(query):
    data = ytdl.extract_info(query)

    if data["extractor"] == "youtube:search":
        # Search results: we only take the first one if it exists
        results = data["entries"]
        if len(results):
            return to_yt_dict(results[0], processed=False)
        else:
            raise NoSearchResultsError

    elif data["_type"] == "playlist":
        # We add the whole unprocessed playlist for speed
        return [to_yt_dict(info, processed=False) for info in data["entries"]]

    else:
        return to_yt_dict(data)
