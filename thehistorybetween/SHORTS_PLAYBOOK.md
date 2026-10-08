# Shorts playbook (the every-2-days routine follows this)

One run = handle what the owner decided on the Shorts Desk, then build ONE new 65-second vertical Short and put it on the desk for review. Nothing is ever posted without the owner's approval.

- Shorts Desk (review page): https://claude.ai/artifact/3J88j7onHVMxhQGYfofVNw
  - database collection `shorts`, one document per Short, id = folder slug (e.g. `001-nobody-shot-me`)
  - `status`: `pending` → owner sets `approved` | `changes` (with `note`) | `rejected` → routine sets `scheduled` / `posted`
- ElevenLabs flow for all generations: `JEwlbDddA505fPjx9XGx`
- Narrator: voice `3YzGaTGef0x5PLEK9yGq` ("Atlas – Deep, Gravelly Narrator"), model `eleven_multilingual_v2`
- Time zone: US Central. Posting slot: 6:00 PM CT.
- Owner notifications: email `gomezdie05@gmail.com` (the address the owner's other routines report to).

## 0. Setup (fresh container)
1. The repo is `GomezDie/notes-app`, branch `claude/youthful-bohr-1wczz7`. If `/home/user/notes-app` is missing, attach it with `add_repo` (owner `gomezdie`, repo `notes-app`, access `push`) and clone it. `git fetch origin claude/youthful-bohr-1wczz7 && git checkout claude/youthful-bohr-1wczz7 && git pull`.
2. `pip install -q pillow`. ffmpeg and fonts are preinstalled.
3. Work in `thehistorybetween/`. Read `README.md` and this file.

## 1. Act on the owner's decisions
`ArtifactData list` on the desk, collection `shorts`.
- **approved**: schedule it for the next 6:00 PM CT slot on TikTok and YouTube Shorts.
  - If a **Metricool** connector is available (tools like `createScheduledPost`): it needs a public MP4 URL. Get one by uploading `shorts/<slug>/build/final.mp4` to the ElevenLabs flow (`creative_create_asset_upload` → PUT the bytes → `creative_finalize_asset_upload`), then read the file's signed URL from the flow (it is valid ~2 h, so schedule right away). Post the same caption + hashtags to TikTok and YouTube Shorts (YouTube title = the doc `title`). Then `update` the doc: `status: "scheduled"`, `scheduledFor` (ISO time), `postedVia: "metricool"`.
  - If Metricool is NOT available: leave it `approved` and say in the email that it is ready to post by hand (the desk has a Download MP4 button).
  - If `shorts/<slug>/build/final.mp4` is missing (fresh container), re-render it first: `python3 pipeline/vshort.py shorts/<slug>/spec.json` (re-download any clips/stills listed in the spec's `elevenlabs` block with `creative_get_flow_run_status`).
- **changes**: rework THAT Short instead of building a new one this run. Read `note`, fix the script/spec/shots, regenerate only what the note requires, re-render, re-upload, set `status: "pending"`, clear `note` (`{"__delete__": true}`), add `revision` +1. Then skip step 2–6 and go to step 7.
- **rejected**: leave it. Note the reason (if any) in `shorts/LOG.md` and avoid repeating the mistake.
- **pending** older than 6 days: mention it in the email ("still waiting for your review").

## 2. Pick the topic
- Take the first unchecked line in `shorts/TOPICS.md`. Keep runs of a series together (e.g. the Capone set) so Shorts feed each other.
- At most one vidIQ call per run (credits are limited): `vidiq_outliers` with the topic keyword to confirm interest and borrow hook ideas. Skip if vidIQ balance < 20.

## 3. Research and script (65 s target)
- Research with WebSearch only (WebFetch is blocked for most sites). Cross-check every number in 2+ sources; prefer museum, archive, government, encyclopedia and university pages.
- Script: **155–170 words** (Atlas reads ~2.65 words/s → 61–66 s). Must end above 61 s total; the renderer pads with the end card if short.
- Shape: one complete story beat. Line 1 drops the viewer into the moment (date + place or a shocking detail). Middle: 3–5 escalating facts. Turn: the twist. Last line: a loop back or a cliffhanger, then "Follow The History Between for …".
- Write numbers as spoken ("nineteen twenty-nine"). No invented quotes; real quotes only with a source. No speculation stated as fact ("reportedly" when sources disagree).
- Save `shorts/<NNN-slug>/script.md` with the script, a fact table (claim → source URL) and the hook line.

## 4. Generate assets (budget ≤ 12,000 credits per Short)
Generate everything on flow `JEwlbDddA505fPjx9XGx`.
| Asset | How | ~Credits |
|---|---|---|
| Narration | `creative_generate_speech`, Atlas, `eleven_multilingual_v2`, `generations_count: 1` | ~1,000 |
| Word timings | pin the take (`creative_add_flow_asset_node`), `creative_transcribe_audio` (Scribe), download `words.json` | ~0 |
| Stills (4–6) | `creative_generate_image` `gpt-image-2`, 2 variations; pick by contact sheet. Vertical: create with `estimate_only`, `creative_update_node` `aspect_ratio: "9:16"`, then `creative_run_flow_nodes` | ~370 each |
| Clips (4–5) | Veo 3.1 Lite (`veo-3.1-lite-generate-001`) from the picked still: create with `estimate_only`, then `creative_update_node` with `{"duration_secs": 4|6|8, "aspect_ratio": "9:16", "resolution": "720p", "generate_audio": false, "negative_prompt": "..."}`, then run. Never leave audio on. Never use Seedance here (7× the price). | ~182/s |
| Music | reuse `episodes/ep01-capone/assets/music_score.mp3` with a different `music_offset`, or generate a 75 s instrumental with `eleven_music_v2_5` (prompt must say instrumental, no vocals) and confirm with Scribe that the transcript is empty | ~0 / ~600 |
- Shared style suffix for every image prompt: "Muted desaturated palette with cold blue shadows and warm sepia highlights, subtle film grain, painterly realism like a high-end documentary reconstruction. No text, no logos."
- Download with `pipeline/fetch.py` (JSON list of {name, url}); signed URLs expire in ~2 h.
- Record every generation's `session_id` + `generation_id` in `spec.json` under `"elevenlabs"` so a later run can re-download.
- If any call returns `quota_exceeded`, stop generating, do not retry, and report it in the email.

## 5. Accuracy gate (do not skip)
Make a contact sheet of every picked still and 3 frames of every clip. Check and fix before rendering:
- headcounts and numbers on screen match the script (ep. 1 lost a lineup shot for showing 6 men instead of 7)
- no invented signs, documents or labels that look real (crop them out or regenerate)
- no modern objects, wrong uniforms, wrong decade
- **no AI-generated faces of real people** — real people appear only as silhouettes, from behind, or via graphics
- every on-screen fact appears in the fact table with a source
Write what you checked as short sentences; they go into the desk's `checks` field.

## 6. Build and render
- `shorts/<NNN-slug>/spec.json`, modelled on `shorts/001-nobody-shot-me/spec.json` (beat types: clip, still, card, quote, stat, lineup, flash, stamp, end; each beat starts at a phrase from the narration). Use graphics cards for numbers and quotes, footage for places and action; change the picture every 2–5 s.
- Preview: `python3 pipeline/vshort.py shorts/<slug>/spec.json --stills <6–8 times>` and look at the stills once; fix overlaps, then render: `python3 pipeline/vshort.py shorts/<slug>/spec.json`.
- Final file for posting and the desk (≤ 15 MB): `ffmpeg -i build/short.mp4 -c:v libx264 -preset slow -b:v 1500k -maxrate 2000k -bufsize 4000k -c:a aac -b:a 128k -movflags +faststart build/final.mp4`. Check: 1080×1920, 61–70 s, −14 to −15 LUFS.

## 7. Put it on the Shorts Desk
1. Upload `build/final.mp4`: `Artifact` publish with `url` = the desk, `asset: true`, `file_path` → note the asset id.
2. `ArtifactData set` collection `shorts`, doc id = slug, fields: `n`, `slug`, `title` (≤ 70 chars, curiosity + clarity), `hook`, `status: "pending"`, `duration`, `credits`, `created` (ISO), `videoAssetId`, `video` ("/_blob/<id>"), `script`, `caption` (1–2 sentences, no clickbait lies), `hashtags` (6–9, always include `history` and `historytok`), `sources`, `checks`, `postPlan`. For a rework, `update` with `if_version` instead.
3. Do not republish the desk page itself.

## 8. Wrap up
- Append a line to `shorts/LOG.md`: date, slug, status, credits used, anything that went wrong.
- Tick the topic in `shorts/TOPICS.md`; add 1–2 new topic ideas when the list has fewer than 8 open.
- Commit: spec.json, script.md, words.json, vo.mp3, LOG.md, TOPICS.md (clips/stills/build stay out of git; their ElevenLabs ids are in the spec). Push to `claude/youthful-bohr-1wczz7` with retries on network errors.
- Email the owner (Gmail connector) subject `TheHistoryBetween — Short #NNN ready for review`: title, hook, the desk link, what was scheduled this run, anything waiting, credits used, problems. If no send tool exists, say so in the final summary.

## Never
- post or schedule anything that is not `approved` on the desk
- generate faces of real historical people, fabricate quotes, or present AI images as real photos
- spend more than ~15,000 credits in one run
- touch other artifacts, routines or repositories
