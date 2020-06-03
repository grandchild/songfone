
# songfone

Download songs from your remote music collection onto your phone — optionally converting
to a different audio codec.

The goal is to have a similar experience to Spotify or Netflix download caches.


## Requirements

* A file synchronization tool *on both the server and the phone*. Any will do, that is
any that copies changed files automatically from *each* side to the other will do.
<br>If you don't know which, I suggest you give [Syncthing](https://syncthing.net) a
try.

### Server requirements

* [Python](https://python.org) >= 3.6
* [mutagen](https://github.com/quodlibet/mutagen)

Optional for codec conversion:
* ffmpeg: [ffmpeg](https://ffmpeg.org)

### Phone requirements

* Android OS


## Setup

### Server

Unpack the `server/` directory on the server machine and configure `"audio"`, the path
to your music libarary in `songfone.conf`:

```json
{
    "audio": "~/Music"
}
```
This is the only *required* configuration.

### Sync

Next set up your file synchronization tool to share `~/.local/share/songfone` with the
device you want to download music to.

You should see a `.songfone/` directory appear as soon as you start the server.

### App

*TODO*


## Configuration

The default share folder is `~/.local/share/songfone`, but you can set its location
anywhere by adding the `"output"` option:

```json
{
    "audio": "~/Music",
    "output": "~/my/songfone"
}
```

You may set multiple audio source paths like this:

```json
{
    "audio": ["~/Music", "~/AudioBooks"]
}
```

When converting songs, you might want to use multiple threads to speed up the process:

```json
{
    "audio": "~/Music",
    "max_conversion_threads": 6
}
```
The default value is `2`, so not setting this will already convert two songs at a time.

This config key supports setting the thread count in relation to the system's CPU count:

```json
{
    "audio": "~/Music",
    "max_conversion_threads": "cpus/2"
}
```
You may use any expression like `cpus [ +|-|*|/ <number> ]`, e.g.: *"cpus-2"*,
*"CPUs \* 2"* or just *"cpus"*. Case and spaces between the operands and operators don't
matter. Conversion might fail if all CPUs are busy with ffmpeg (*TODO: Why?*), so a
recommended setting would be *"cpus-1"*.

Other options can be found in [`config.py`](server/config.py) as attributes of
the `Config` class.


## TODO

* *android app*
* cover art
* (multiple servers)


## License

[![License](https://img.shields.io/github/license/grandchild/songfone.svg)](
    https://creativecommons.org/publicdomain/zero/1.0/)

You may use this code without attribution, that is without mentioning where it's from or
who wrote it. I would actually prefer if you didn't mention me. You may even claim it's
your own.
