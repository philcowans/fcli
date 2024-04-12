# FCLI

FCLI is an experimental command line Mastodon client. The goals of the project are:

* To experiment with 'algorithms' to manage post volumes. Currently the number
of posts reviewed per session is limited to 50, and feedback (interesting /
not interesting) is recorded for all posts which are reviewed. This is used to
prioritise posts from accounts known to post a high percentage of high quality
posts.

* To provide a 'workflow' based interface, i,e. posts are reviewed in order and
next actions must be decided before moving on to the next post.

* To integrate into broader personal information management processes, in
particular project and goal tracking, reading list management and next action
tracking.

The software is currently at a very stage of development, but I am using it on
a daily basis. Please let me know if you're interested in the project.

## Installation

FCLI is a python project, so you'll need a working python environment.
Requirements are listed in `requirements.txt` in the usual way.

This guide is for installation on Linux (which I use) - you'll need to vary
things (and probably also edit the code) to make it work on other platforms.

You'll need to register a Mastodon app at your instance. You can do this using
`curl` with somethign like the following:

```
curl --form 'client_name=fcli' --form 'redirect_uris=urn:ietf:wg:oauth:2.0:oob' --form 'scopes=read write' https://<instance hostname>/api/v1/apps
```

The app also depends on Everdo (which I personally use for my own information
management workflows). You'll need to configure it to expose a local API. 

Configuration is via an INI file in `{$HOME}/.config/fcli/config.ini`:

```
[Mastodon]
Server = <instance hostname>
Username = <username>
ClientID = <client ID from app registration>
ClientSecret = <client secret from app registration>

[Everdo]
Key = <API key>
```

Finally, you'll need to create some directories to store state:

```
{$HOME}/.fcli/cache
{$HOME}/.fcli/outbox
{$HOME}/.fcli/processed/actionable
{$HOME}/.fcli/processed/actioned
{$HOME}/.fcli/processed/boostable
{$HOME}/.fcli/processed/boosted
{$HOME}/.fcli/processed/interesting
{$HOME}/.fcli/processed/not_interesting
{$HOME}/.fcli/processed/skipped
{$HOME}/.fcli/sent
{$HOME}/.fcli/staging
```

There are probably other things you need to do - my isntallation has evolved
with the codebase, so let me know if you run into any problems.

## Usage

Kick off the workflow using the default entry point:

```
python -m fcli
```

You'll be asked to authenticate via an OAuth 2.0 code. This step will also post
the content of any files in `{$HOME}/.fcli/outbox`.

There are a few command line options you'll find if you look at the code, but they're obsolete.
