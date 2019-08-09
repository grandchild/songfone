
# songfone

Download songs from your remote music collection onto your phone — optionally converting
to a different audio codec.

The goal is have a similar experience to Spotify or Netflix download caches.


## Requirements

* A file synchronization tool *on both the server and the phone*. Any will do, that is
any that copies changed files automatically from *each* side to the other will do.
<br>If you don't know which, I suggest you give [Syncthing](https://syncthing.net) a
try.

### Server requirements

* [Python](https://python.org) >= 3.6
* [ffmpeg](https://ffmpeg.org) or [libav](https://libav.org)
    ([pydub-related install instructions](
        https://github.com/jiaaro/pydub#getting-ffmpeg-set-up))
* [pydub](https://github.com/jiaaro/pydub)

### Smartphone requirements

* Android OS


## Setup

* Unpack the server source on the server and configure `songfone.conf`:

```json
{
    "audio": "~/Music"
}
```

`"audio"`, the path to the music libarary is the only practically required option.

The default share folder that you will have to sync is `~/.local/share/songfone/output`,
but you can set its location anywhere by adding the `"output"` option:

```json
{
    "audio": "~/Music",
    "output": "~/my/songfone/output"
}
```

Other options can be found in [`server/config.py`](server/config.py)

## TODO

* *android app*
* actual database *update* instead of replacement
* multiple audio dirs
* (multiple servers)

## License

[![License](https://img.shields.io/github/license/grandchild/songfone.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

You may use this code without attribution, that is without mentioning where it's from or
who wrote it. I would actually prefer if you didn't mention me. You may even claim it's
your own.
