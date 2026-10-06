# TheHistoryBetween — video pipeline

History documentaries in the “armchair documentary” style (cold open → named chapters → numbered beats → ending that loops back), 10–20 min long-form, plus Shorts cut from each episode.

## Layout

```
pipeline/
  align.py    sentence timings from narration audio (pause detection + DP, no speech model needed)
  gfx.py      motion-graphics engine: brand palette/fonts, Ken Burns, crossfades, grain, audio mix, SRT
  shorts.py   9:16 Short from a sentence range: blurred fill, hook line, big captions, CTA
episodes/
  ep01-capone/
    script.md       research, full outline, cold-open VO + visual cues, Shorts list, sources
    coldopen.py     scene code for the cold open
    assets/         narration takes, sentences.txt, timing.json, images
    build/          renders (git-ignored)
```

## Make an episode segment

```bash
pip install pillow
cd episodes/ep01-capone
python3 ../../pipeline/align.py assets/vo_take1.mp3 assets/sentences.txt assets/timing.json
python3 coldopen.py stills 5 30 60      # preview frames
python3 coldopen.py render              # -> build/ep01_coldopen_1080p.mp4 + .srt
python3 ../../pipeline/shorts.py build/ep01_coldopen_1080p.mp4 assets/timing.json 9 27 \
  "HIS LAST WORDS WERE A LIE" "Full story: THE HUNT FOR AL CAPONE" build/short01_nobody_shot_me.mp4
```

`sentences.txt` must hold the narration exactly as spoken, one sentence per line (spell out numbers the way the narrator says them). That keeps the alignment accurate.

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
- Music: `make_music()` produces a placeholder drone. Swap in licensed music (Epidemic Sound, Artlist, YouTube Audio Library) before publishing.
