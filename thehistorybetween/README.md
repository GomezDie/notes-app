# TheHistoryBetween — video pipeline

History documentaries in the “armchair documentary” style (cold open → named chapters → numbered beats → ending that loops back), 10–20 min long-form, plus Shorts cut from each episode.

## Layout

```
pipeline/
  align.py    sentence timings: from word timestamps (ElevenLabs Scribe words.json), or pause detection
  gfx.py      motion-graphics engine: brand palette/fonts, Ken Burns, video clips, crossfades, grain,
              ducked music mix with offset, loudness normalisation, SRT
  shorts.py   9:16 Short from a sentence range: blurred fill, hook line, word-timed captions, CTA
  fetch.py    download a batch of generated files from a JSON list of {name, url}
episodes/
  ep01-capone/
    script.md       research, full outline, cold-open VO + visual cues, Shorts list, sources
    coldopen.py     scene code for the cold open
    assets/         narration takes, sentences.txt, words.json, timing.json,
                    stills/ (approved AI stills), clips/ (AI B-roll), music_score.mp3
    build/          renders (git-ignored)
```

## Make an episode segment

```bash
pip install pillow
cd episodes/ep01-capone
python3 ../../pipeline/align.py --words assets/words.json assets/vo_take1.mp3 assets/sentences.txt assets/timing.json
python3 coldopen.py stills 5 30 60      # preview frames
python3 coldopen.py render              # -> build/ep01_coldopen_1080p.mp4 + .srt
python3 ../../pipeline/shorts.py build/ep01_coldopen_1080p.mp4 assets/timing.json 9 27 \
  "Shot 14 times. His last words:" "Full story → THE HUNT FOR AL CAPONE" build/short01_nobody_shot_me.mp4
```

`sentences.txt` must hold the narration exactly as spoken, one sentence per line (spell out numbers the way the narrator says them). That keeps the alignment accurate.

## Generating assets (ElevenLabs, all on one flow per episode)

| Asset | Model | Settings that matter | Cost seen (Oct 2026) |
|---|---|---|---|
| Narration | `eleven_multilingual_v2`, voice “Atlas – Deep, Gravelly Narrator” | spell numbers as spoken | ~1,700 credits per 2-min take |
| Stills | `gpt-image-2` | 16:9, period prompt + shared style suffix, 4 variations, pick 1 | ~185 credits each |
| B-roll | **Veo 3.1 Lite** image-to-video from the picked still | `generate_audio: false`, 4–8 s, 720p, negative prompt | ~182 credits/second (8 s ≈ $0.26) |
| Music | `eleven_music_v2_5` | describe the arc; check with Scribe that it has no vocals | ~900 credits per 2 min |
| Word timings | `eleven_scribe_v1` on the narration | gives exact captions + scene sync | free / small |

Notes:
- Seedance 2.5 costs ~7x more than Veo Lite here ($3.05 vs $0.44 for one clip), so Veo Lite is the default. Use Veo 3.1 Fast (~$1.32 / 8 s) only for hero shots.
- Turning video audio off cuts Veo Lite cost by ~40%. The episode mix uses its own music and sound.
- Generate stills first, pick, then animate the pick. Clips keep the look of the still, which keeps an episode consistent.
- Check every AI shot for history problems: count people (ep. 1's lineup shots showed 6 men, not 7, so they were dropped), invented signs (cropped out of the ledger shot), modern objects.
- Music: line up the score's big moment with the story beat using `music_offset` (ep. 1: the hit lands on “Then the officers open fire”).

Ep. 1 cold open total: ~17,800 credits (about $3.25 at the rates ElevenLabs reported), plus the narration.

## Brand

| token | value | use |
|---|---|---|
| INK | `#0E0D0B` | background |
| PAPER | `#E9E1CF` | primary text |
| GOLD | `#C9A45C` | labels, accents |
| RED | `#B3261E` | danger, strike-throughs, stamps |
| BLUE | `#5678A0` | police / authority |

Type: Liberation Serif (titles, quotes), Liberation Sans Bold tracked caps (labels), Liberation Mono (date stamps, documents).

## Rules for the channel
- No AI-generated faces of real people. Use real archival photos (public domain) or silhouettes and graphics.
- Mark illustrative material as illustrative (e.g. recreated headlines).
- Every number in a script needs a source in the episode's `script.md`.
- Tick YouTube’s “altered or synthetic content” box when realistic AI imagery is used.
- Music: use generated (ElevenLabs Music) or licensed tracks (Epidemic Sound, Artlist, YouTube Audio Library). `make_music()` is only a placeholder drone.
