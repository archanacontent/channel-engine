# Channel Engine

Six faceless Shorts channels, rendered and posted from one repo at no cost. Every Short starts from a dated public record, gets a human approval on Sunday, and goes public only at its slot.

| Channel | Topic | Daily source |
| :--- | :--- | :--- |
| Asked & Answered | B2B marketing for AI search | [Asked](https://archanacontent.github.io/asked/) and sourced 2026 news |
| The Automation Shelf | Free marketing automations | n8n workflows that pass the n8n validator |
| Breach Brief | Exploited flaws, breaches, scams | CISA KEV, NVD, SEC and FTC |
| Plain Docs | Technical writing for beginners | Openly licensed public docs |
| Deep Field | Space science | NASA open media and fact pages |
| Viksit Bharat On Record | India's progress, one verified figure a day | PIB releases posted in the last 10 days |

## How A Short Is Made

1. An episode file in `channels/<slug>/episodes/` holds the script beats, the record they came from and the description.
2. `render/audio.py` voices each beat with Kokoro-82M, an Apache 2.0 model that runs on the Actions runner.
3. `render/painters/<slug>.py` draws every frame in the channel's palette and fonts, and `render/lib.py` adds the captions.
4. `render/build.py` encodes 1080 x 1920 H.264 with AAC audio and writes the YouTube and Instagram metadata beside the video.

```bash
bash scripts/setup_models.sh
pip install -r requirements.txt
python -m render.build channels/breach-brief/episodes/2026-11-10-openssh-cve-2026-123158.yaml --out out
```

Add `--stills 3,12.5` to save single frames instead of rendering the whole video. `python -m render.channel_art` redraws every channel's profile image, banner and watermark into `channels/<slug>/art/`.

## Viksit Bharat On Record

One Short a day at 09:00 New York (19:30 in India). The weekday sets the series: Myth vs Record on Monday, Thursday and Saturday, While the World on Tuesday and Friday, Then vs Now on Wednesday and Sunday. `sources/vb.py` rotates 20 sectors on a 21-day cycle and takes only PIB releases posted in the last 10 days.

Every script passes two checks before review: the writer's own check that each figure appears in the release, and `pipeline/factcheck.py`, a second read that rejects any line the release doesn't support. At the slot, `review/slot_check.py` holds a Short if its release is offline or older than 21 days.

`pipeline/looks.py` gives each Short a palette, a background motion and a hook style. No palette or motion repeats within 8 Shorts and no combination repeats within 21 days. The first beat is the hook and doubles as the thumbnail, saved as `<stem>-thumb.jpg` beside the Short.

## Brand Files

`channels/<slug>/brand.yaml` is the single source for a channel's palette, fonts, voice, music, caption style, series and slots, title formulas, description template and hashtags. Change a colour or a voice there and every later render follows.

## Music

`render/music.py` composes an original track for every Short: its own key, mode, chord progression, tempo, groove and melody, in the channel's style. `channels/<slug>/music/used.json` records each track, and a repeat on the same channel is rerolled. Nothing is licensed, so nothing can draw a Content ID claim.

## Posting And Review

- Sunday: the week's Shorts upload to YouTube as private, and a GitHub issue lists each one with a checkbox.
- At 09:00, 13:00 and 18:00: `post-slot.yml` publishes only the Shorts ticked in that issue.

Secrets needed: `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and one `YT_REFRESH_<SLUG>` per channel.

## Licences Of What Ships In The Repo

- Fonts in `assets/fonts/`: SIL Open Font License, from [google/fonts](https://github.com/google/fonts).
- Voice model: Apache 2.0, downloaded at run time from [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).
