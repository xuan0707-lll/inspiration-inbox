# Inspiration Inbox

[简体中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md)

[Download the preview](https://github.com/xuan0707-lll/inspiration-inbox/archive/refs/tags/v0.1.0-alpha.2.zip) · [Download the iPhone shortcut](https://github.com/xuan0707-lll/inspiration-inbox/raw/refs/heads/main/mobile/存到灵感库.shortcut) · [Setup](#setup)

Turn videos and image posts you come across on your phone into Obsidian notes you can use with AI for writing, research and creative work.

**The first release is for an Apple silicon Mac and an iPhone.** Both devices need Obsidian and iCloud Drive sync. You can save a link from your phone at any time. Transcription runs locally on your Mac, with no transcription minutes or AI credits to buy. If your Mac is asleep or turned off, shared links wait in the inbox until the Mac is awake, online and running the background service again.

Currently supported platforms are **Douyin, Bilibili and Xiaohongshu (RedNote)**. Each video note keeps the original link and the post description when available. Spoken content is transcribed into paragraphs, given a short title based on the content and followed by an outline.

## 1. Automatic video transcription

When you find a useful video, **copy its link and tap “Save to Inspiration Inbox” in iPhone Control Center**. You can carry on browsing while your Mac takes care of transcription and formatting. Later, even a single keyword you remember from the video can help you find the passage in Obsidian and quote it. Videos that might otherwise gather dust in your favorites become material you can actually use, without hunting for the original, replaying it or typing out the transcript.

## 2. Text from image posts and a first look at video visuals

For a Xiaohongshu image post, copy the link and tap “Save to Inspiration Inbox” as usual. Your Mac reads the text in each image and keeps it under a separate heading in the original order, alongside the post description and source link. If a tutorial spreads its instructions across several images, you can search for a keyword to find the relevant page or let an AI assistant work directly with the extracted text.

If it is the **visuals or animation** that caught your eye, select “Save to Inspiration Inbox” from the share sheet and add a note such as “Look at the title animation in the first three seconds.” The tool saves your comment with the link and samples frames for a preliminary description. An AI assistant with access to your vault can then see what you wanted to learn from the clip. (Frame sampling can miss changes between frames. To check how a title appears or which way a person moves, an assistant with video access can follow the link and inspect the original.)

## 3. Automatic transcription of new posts from creators you follow

Add a Douyin creator you want to keep up with. While your Mac is online, it checks the creator’s public page periodically. The first check records existing posts. When a new one appears, the Mac transcribes it and saves it in a separate Obsidian folder called “Followed Creators.” There are no individual links to copy. When a favorite creator posts a twenty-minute video, you can read the outline first, find the part you care about and decide what to watch. (The first release supports Douyin creators added manually. After a long time offline, the Mac may miss posts that have already dropped off the public list.)

## How it works

The iPhone shortcut writes the shared link and any comment to the “Mobile Share Inbox” in Obsidian. iCloud syncs the entry to your Mac. The service uses platform subtitles when it can retrieve them and otherwise transcribes the audio locally with Whisper `large-v3-turbo`. Image text recognition and preliminary frame analysis also run on the Mac. The results are saved as Markdown notes in Obsidian. The tool is free to download and use, and the default local workflow has no transcription or AI usage fees. (Automatic transcripts can mishear names, numbers and technical terms. Each note includes the source link so you can check.)

## Why it exists

Inspiration Inbox helps turn things you discover on your phone into material you can revisit with an AI assistant. For example, when drafting an article about video production, an assistant with access to your vault can find where several creators discuss the same issue, compare their approaches and include links to the original videos. A quick comment added when saving a link can give you a way back to that idea on your next project.

## What’s next

Automatic categorization and Windows compatibility testing are in preparation. Android support is also planned. Platforms under consideration include X, YouTube, TikTok and Instagram, as well as Toutiao, WeChat Official Accounts and Zhihu. These are examples, and other sources will be explored as needs emerge.

Keeping capture convenient on a phone will remain a priority. Use GitHub Issues to tell us where you would like to collect material from or which step still feels cumbersome. That feedback will help guide platform support and future features.

## Setup

Version v0.1.0-alpha.2 fixes inbox startup at Mac login and verifies folder access. The downloadable package currently uses Chinese filenames and interface labels. The names above are their English equivalents. Use the vault name below exactly as shown for this version.

1. Install Obsidian on both devices and enable iCloud Drive under the same Apple Account. On iPhone, create or open the vault named `灵感与素材` (“Inspiration and Materials”) with Store in iCloud enabled. When it appears in Finder under iCloud Drive → Obsidian, open that folder as a vault on the Mac.
2. Download and extract the ZIP on your Mac. Double-click `一键配置.command` (one-click setup). The first run needs internet access to download several GB of tools and models. If prompted, install Apple’s Command Line Tools and rerun setup. Confirm “Add Shortcut” when the import window appears.
3. With Shortcuts iCloud sync enabled, add the synced shortcut to iPhone Control Center using Add a Control → Shortcuts. You can also download the shortcut directly on the iPhone. Try a short Bilibili video and check the “Video Inspiration” folder after your Mac processes it. To follow a Douyin creator, open `添加特别关注.command` (add a followed creator) and paste the public Douyin Jingxuan creator page URL.

[Detailed setup and troubleshooting in Chinese](README.md#第一次使用) · [MIT License](LICENSE)
