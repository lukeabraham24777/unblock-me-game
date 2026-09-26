# Higgsfield AI: Research Report and Replication Spec

Date: 2026-09-26

## How this was produced

Two passes. First, the deep-research workflow (1 scoping agent, 5 search agents, 28 fetch agents, 7 adversarial verification votes), stopped at 37 agents to respect a credit cap. Second, six targeted research agents on the gaps the first pass left (orchestration and "reference anchors", Layers and relighting, Cinema Studio and post-processing, identity features, DoP internals, API and company). Everything was then synthesized by hand.

A caveat on provenance: higgsfield.ai and its subdomains, arxiv.org, wikipedia.org, techcrunch.com, x.com and most third-party blogs were blocked by the sandbox egress proxy. Quotes from those hosts were recovered from search-engine snippets of the same pages. Higgsfield's own GitHub repositories (`higgsfield-ai/cli`, `higgsfield-ai/higgsfield-js`, `higgsfield-ai/skills`, `higgsfield-ai/soul-voice-service`) and PyPI packages were fetched directly and are the most reliable first-party evidence in this document.

Evidence grades:

| Grade | Meaning |
|---|---|
| **A** | Verified by 3-vote adversarial check, or stated in Higgsfield source code / more than one first-party page and corroborated independently |
| **B** | Stated on one first-party page (help center, blog, product page, SDK) or by one reputable third party |
| **C** | Inference from B-grade facts plus published research; Higgsfield has not confirmed it |

---

## 1. What Higgsfield actually is

Higgsfield is three layers stacked on each other (grade A):

1. **An aggregator.** 50+ licensed image, video and audio models sold under one credit pool and one API: Seedance 2.0 / 2.0 Mini / 2.5 (ByteDance), Kling 3.0 and Kling O1 (Kuaishou), Veo 3.1 (Google), Sora 2 (OpenAI), Wan 2.6 / 2.7 (Alibaba), Hailuo 2.3 (MiniMax), LTX, PixVerse, Nano Banana 2 / Nano Banana Pro (Google Gemini image), GPT Image 2 (OpenAI), Seedream 4 / 5 (ByteDance), FLUX 2 and FLUX Kontext, Recraft, Ideogram, Grok, Seed Audio, ElevenLabs, MiniMax speech, Sync Labs lipsync-2, InfiniteTalk, Topaz upscaling. Its own help center routes users: "Seedance handles realistic motion and Kling handles longer or multi-shot clips, with Higgsfield DOP adding VFX and cinematic camera control."
2. **In-house models** where the founders believed they could win: **Soul** (image family: Soul, Soul 2.0, Soul Cinema), **Soul ID** (trained identity), **DoP** (image-to-video with camera control, diffusion plus RL), **Soul Voice** (open-source voice design and cloning service), **Speak** (lipsync), and an undisclosed face-swap engine.
3. **A control and orchestration layer** that is the actual product: **Elements** (@-taggable characters, locations, props reused across every model), **Cinema Studio** (camera bodies, lenses, focal lengths, motion presets, an AI Director built on Claude), **Canvas** (node graph over all models), **Supercomputer** (an agent that takes a brief and plans, routes and generates), **Marketing Studio**, **Popcorn** (storyboard/keyframes), **Layers** (ML layer decomposition and editing), **Relight** and **Color Palette** (image and video), **Lip-Sync Studio**, **Higgsfield Audio**, plus prompt enhancement, a Figma plugin, an MCP server, a CLI and human-authored "Skills".

The "just a wrapper" critique is half right: raw video pixels mostly come from licensed models, and Higgsfield's own quality does not beat Kling or Runway head-to-head in third-party reviews. What is not a wrapper: DoP, Soul, Soul ID, the intent-capture UX, the Elements system, the agentic orchestration, the data and captioning pipeline, and the sheer breadth of normalized model access.

### Company facts

| Item | Value | Grade |
|---|---|---|
| Founded | 2023, San Francisco and Almaty | B |
| Founders | Alex Mashrabov (CEO; ex-Snap Director of Generative AI; co-founded AI Factory, sold to Snap in 2020 for $166M, became Snapchat Cameos), Yerzat Dulat (CTO; deep RL background, author of the `higgsfield` GPU orchestration framework), Mahi de Silva (CSO) | B |
| Headcount | ~454 as of July 2026; CEO has said ~60 engineers | B |
| Seed | $8M, Menlo Ventures, Apr 2024 | B |
| Series A | $50M, GFT Ventures, Sept 2025, $1.0B valuation; $80M extension led by Accel, Jan 2026, $1.3B | B |
| Series B | $400M, DST Global lead with Goldman Sachs Alternatives, Valor, Tribe; Aug 2026; $5.4B valuation | B |
| Revenue | ~$200M ARR Jan 2026; ~$500M ARR mid-2026 (SaaStr talk); $700M annualized July 2026; cash-flow positive; $1B ARR target | B |
| Compute | Google Cloud Vertex AI / AI Hypercomputer for the 2024 foundation model; Nebius (Blackwell) and TensorWave (AMD MI300X) for DoP; NVIDIA and Together AI partnerships after Series B | A/B |
| Prior product | Diffuse (Apr 2024) and Diffuse 2.0 (Aug 2024): selfie-to-personalized-clip app on a custom diffusion-transformer video model | B |
| Controversy | Dec 2025 mass bans of "unlimited" users (Higgsfield said 99% fraud, ~40k bot accounts, $1.35M refunded); Kling publicly said "There is no Kling Unlimited"; Higgsfield's X account was suspended Feb 9, 2026 | B |

Founder strategy, from a Google Cloud case study (A): build only the pieces where you can win in-house, license the rest. The in-house video model was scoped narrowly to "people being people": faces, expressions, dynamic camera and lighting. CEO in a Sacra interview (B): Higgsfield's edge is curation plus "own fine-tuned and post-trained models", not a marketplace.

---

## 2. System architecture (target for replication)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Surfaces: web app · Canvas · Cinema Studio · Marketing Studio ·          │
│           Supercomputer chat · Figma plugin · CLI · MCP · REST API       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ jobs
┌──────────────────────────────▼──────────────────────────────────────────┐
│ Orchestration                                                            │
│  • Supercomputer agent: planner + router + 40+ tools + 3 memory layers   │
│  • Mr. Higgs / Claude AI Director (Cinema Studio): shot breakdown,       │
│    setting changes, prompt drafting; never triggers generation itself    │
│  • Prompt enhancer (enhance_prompt=true by default)                      │
│  • Elements registry: characters / locations / props, @tag resolution    │
│    into each model's native reference slots                              │
│  • Model families → latest version; capability negotiation; credits      │
└───┬──────────────┬──────────────┬───────────────┬──────────────┬────────┘
    │              │              │               │              │
┌───▼────┐   ┌─────▼─────┐  ┌─────▼──────┐  ┌─────▼─────┐  ┌─────▼──────┐
│In-house│   │ Licensed  │  │ Identity   │  │ Edit stack│  │ Audio      │
│Soul 2.0│   │ Seedance  │  │ Soul ID    │  │ Layers    │  │ Seed Audio │
│Soul    │   │ Kling Veo │  │ Face Swap  │  │ Relight   │  │ ElevenLabs │
│Cinema  │   │ Sora Wan  │  │ Animate    │  │ Gen Fill  │  │ Soul Voice │
│DoP     │   │ Hailuo …  │  │ (WAN 2.2)  │  │ Edit Text │  │ Speak v2   │
│Speak   │   │ NB Pro    │  │ Char Swap  │  │ Remove BG │  │ Lip-Sync   │
│        │   │ GPT Image │  │ (Kling O1) │  │ Color Pal │  │ Studio     │
└───┬────┘   └─────┬─────┘  └─────┬──────┘  └─────┬─────┘  └─────┬──────┘
    └──────────────┴──────────────┴───────────────┴──────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│ Post: Upscale (Topaz engine · ByteDance engine to 4K/60fps) · deflicker  │
│       · Skin Enhancer · Relight · dubbing · mux · C2PA                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Aggregation layer and public API

### Evidence (grade A unless noted; from official SDKs and docs snippets)

- **Base URL and auth.** `https://api.higgsfield.ai`, header `Authorization: Key KEY_ID:KEY_SECRET`. SDKs: `@higgsfield/client` (npm), `higgsfield-client` (PyPI, 0.2.0, Sept 2026, sync and async, file uploads, an "Agent API"), `@higgsfield/cli`, and an MCP server at mcp.higgsfield.ai.
- **Endpoint scheme.** `POST /{model_id}` submits and returns immediately with `request_id`, `status_url`, `cancel_url`; `GET /requests/{id}/status`; `POST /requests/{id}/cancel`. Statuses: `Queued, InProgress, Completed, Failed, NSFW, Cancelled`. Webhooks with a shared secret, or client-side polling. Model ids look like `bytedance/seedream/v4/text-to-image`, `kling-video/v2.5-turbo/pro/image-to-video`, `minimax/hailuo-2.3/standard/text-to-video`, `higgsfield-ai/soul/standard`, `/v1/image2video/dop`, `/v1/text2image/soul`, `/v1/speak/higgsfield`. This is the fal.ai endpoint convention.
- **Common parameters.** `prompt, aspect_ratio, seed, safety_tolerance, model, input_images[{type:'image_url', image_url}], width_and_height, quality, batch_size, style_id, style_strength, custom_reference_id, custom_reference_strength, input_image, input_image_end_url, input_audio, duration, resolution, camera_fixed, motions[{id, strength}], enhance_prompt, webhook_url, webhook_secret`.
- **Rate limits.** An API key "unlocks 20 concurrent requests", raised with top-up volume; 429 on excess. SDK retries 3 times with 1 s to 60 s backoff.
- **Billing.** API is pay-as-you-go from a USD balance (minimum top-up $5, automatic volume discounts). Video priced per second of output, images per image, DoP per generation. Examples: Kling 3.0 10 s clip $1.12; Sora 2 $0.112/s without audio; Seedance 2.0 $0.24 to $0.30/s at 720p; Nano Banana Pro 2K image about $0.134 (B).
- **Family routing.** Web users pick a model family; the platform uses the latest version and new versions become default (A).
- **Subscriptions (B, sources conflict on exact numbers).** Tiers renamed twice in 2026; as of Aug 2026: Basic $9/mo (120 credits), Pro $23 to $29/mo (600 to 900 credits), Max $59 to $79/mo (1,800 to 5,400 credits), plus per-seat Team and Scale. Subscription credits expire each billing cycle with no rollover; packs and auto-refill credits expire after 90 days; $1 is about 20 credits. "Unlimited" is a time-boxed generation mode attached to selected models (`use_unlim: true` in the web client), with fair-use throttling and a reduced concurrency of fewer than 8.

### Replication spec

- **Model registry.** `ModelFamily {family, versions[], default_version, provider_adapter, capabilities{t2i, i2i, t2v, i2v, v2v, ref_images_max, ref_videos_max, ref_audio_max, start_frame, end_frame, native_camera_controls[], multi_shot, duration_range, resolutions, audio_out}, price{per_second | per_image | per_generation}}`.
- **Provider adapters.** One per vendor, normalizing to a `GenerationRequest` and back. Keep a per-model "prompt style card" for the enhancer (section 5).
- **Async job API.** Mirror the fal-style scheme above exactly; it is what every third-party integration expects. Persist `request_id -> {status, outputs, lineage}`.
- **Credit ledger.** Reserve at submit, settle at completion, refund on failure or NSFW. Separate buckets for subscription credits (expire per cycle), purchased credits (expire 90 days) and an API USD balance.
- **Concurrency governor.** Per-key concurrency (start at 20) and per-vendor global concurrency, with vendor fallback inside a family when a vendor is down. Never sell "unlimited" without a rate governor; Higgsfield's Dec 2025 incident is the cautionary tale.

---

## 4. Realism

### Evidence

- **Narrow in-house foundation model (A).** 2024 Google Cloud case study: the model targets "more life-like faces and expressions, dynamic camera movements and lighting", trained on petabytes of video. Menlo Ventures (B): a diffusion transformer combining latent diffusion with transformers, trained on "vast real-world data".
- **VLM captioning (A).** Gemini is used "for video understanding and control over video generation, and video captioning with highly accurate captions that deliver 50% better matching than competitors."
- **Preference post-training (B).** Soul 2.0 is "trained and tuned in collaboration with photographers" and "rooted in preference optimization based on human feedback from art directors."
- **Routing for realism (A).** Seedance for human motion, expression and scene dynamics; Kling for long, multi-shot and physically coherent motion.
- **Prompt enhancer (A).** `enhance_prompt` is an explicit API flag, default true; marketing copy says it is "powered by large language models" and expands brief descriptions "into detailed prompts" with "cinematically appropriate elements". The LLM behind the generic enhancer is not named; the Cinema Studio director is Claude.
- **Upscaling is licensed (A).** Aug 2025: "Higgsfield Upscale integrates technology from Topaz Labs", one-click to 4K. Later a second "ByteDance Upscale" engine "raises video to 4K with frame interpolation up to 60fps"; guidance says use Topaz "for fine restoration, face enhancement, or slow-mo". The upscaler page also promises to "remove flicker, and sharpen details".
- **Skin Enhancer (B).** One of "80 purpose-built creative tools"; engine unstated.
- **Independent quality (B).** Pollo.ai: "good for camera effects but not better than Kling & Runway." Hack'celeration 3.6/5. Wink: Soul has "the best skin texture but the worst likeness consistency". No controlled A/B of Higgsfield-routed vs direct-API Seedance/Kling output exists.

### Replication spec

**4.1 Data and captioning pipeline (the real moat)**

1. Ingest licensed and scraped video; shot-segment with TransNetV2; keep clips 2 to 10 s.
2. Filter: humans present (RetinaFace hit rate), motion band (RAFT mean flow between the 20th and 95th percentile), aesthetic score (LAION v2 above 5), no burned-in text (OCR), no watermark.
3. Camera trajectories via VGGSfM or MegaSaM; discard SfM failures.
4. Caption every clip with a VLM (Gemini 2.x class, or self-hosted Qwen2.5-VL 72B) into a fixed schema:
   ```
   {subject, action, expression, wardrobe, environment, time_of_day,
    lighting{key, fill, rim, color_temp, quality},
    camera{shot_size, angle, move, body, lens_mm, aperture, dof, speed_ramp},
    style{film_stock, grade, era}, audio_hint, negative_traits}
   ```
   plus a prose rendering. Train with random field dropout so sparse prompts still work.
5. Dedupe by ViCLIP embedding cosine above 0.95.

Target 10 to 50M clips.

**4.2 Base video model.** Start from Wan 2.2 14B (or HunyuanVideo) and continue pre-training on the human-centric corpus at 480p, then 720p, then 1080p. This matches the CEO's "fine-tuned and post-trained" description. Then preference post-training: 50k pairwise judgments on skin, hands, eyes and motion naturalness from professional art directors (Higgsfield's stated source), a VLM-based reward model, and Flow-GRPO or DPO on the DiT.

**4.3 Base image model (Soul).** Start from a FLUX-class DiT; continue pre-train on 100M+ fashion, portrait and editorial images captioned with the same schema; post-train with art-director preferences. Ship three checkpoints matching Soul, Soul 2.0 and Soul Cinema (the last with a film-look LoRA and grain profile baked in). Distill to 8 steps.

**4.4 Prompt enhancer.** One VLM call before every generation: inputs are user text, references, preset, optics; output is the schema, rendered in the target model's style card. Faithfulness rule: never add subjects or actions the user did not imply, only lighting, lens and composition detail. Expose as `enhance_prompt` defaulting to true. Cache by input hash.

**4.5 Post chain**

| Stage | Component |
|---|---|
| Upscale to 4K | License Topaz Video AI as Higgsfield did, or SeedVR2 / a Wan-based tile upscaler; add RIFE or a diffusion interpolator for 60 fps |
| Deflicker | All-in-one deflicker (Lei 2023) or flow-aligned temporal filter |
| Skin | RetinaFace crop, GPEN or CodeFormer at fidelity 0.3 to 0.5, soft-mask blend |
| Relight / palette | Section 9 |
| Audio | Section 10 |
| Provenance | C2PA manifest on every export |

---

## 5. Conveying visual intent beyond words

Higgsfield's core product idea: wherever language fails, replace it with a selectable structured control, and keep those controls out of the prompt box. A third-party reverse-engineered skill file for Cinema Studio states the rule outright: "Everything selectable in the Higgsfield UI stays out of the prompt. The prompt field is for scene description only."

### Evidence

| Control | Details | Grade |
|---|---|---|
| DoP motion presets | 50 to 100+ named moves in categories Effects, Basic Camera Control, Epic Camera Control; each has `{id, name, description, preview_url, start_end_frame}`; applied with `strength` 0 to 1 | A |
| Cinema Studio 1.0 (Dec 18, 2025) | 4 camera options: Modern, DV Camcorder, 35mm Film, 8mm Film; 35mm "adds grain structure, tonal response, and analog warmth, modeled at generation time" | B |
| Cinema Studio 2.0 | 6 camera bodies, 11 lenses, focal 8 to 50 mm, spherical vs anamorphic; originally branded (RED, Sony, IMAX, ARRI, Panavision), later de-branded to generic names: bodies "Premium Large Format Digital, Classic 16mm Film, Modular 8K Digital, Full-Frame Cine Digital, Studio Digital S35, Grand Format 70mm Film"; lenses "Creative Tilt, Compact Anamorphic, Halation Diffusion, Extreme Macro, 70s Cinema Prime, Warm Cinema Prime, Swirl Bokeh Portrait, Vintage Prime, Classic Anamorphic, Clinical Sharp Prime"; focal 8/14/35/50 mm; apertures f/1.4, f/4, f/11; 18 motion presets (Static, Handheld, Zoom In/Out, Camera Follows, Pan L/R, Tilt Up/Down, Orbit, Dolly In/Out/L/R, Jib Up/Down, Drone, 360 Roll); speed ramps Linear, Slow Mo, Speed Up, Impact, Auto, Custom; up to three stacked camera movements in 4.0 | B |
| Cinema Studio engines | Image modes use Soul 2.0, Nano Banana 2 or Soul Cinema; video modes route to Seedance 2.0/2.5, Kling 3.0, Veo 3.1, Wan 2.7, Sora 2; 4.0 runs on Seedance 2.5 and accepts up to 50 references; Higgsfield says it "applies camera control logic across all of Higgsfield's generation models" | B |
| AI Director ("Mr. Higgs", Cinema Studio 3.5) | A Claude chat that "adjusts Genre, Style, and Camera settings through conversation", "can break a script into individual shots with camera parameters pre-filled", "sees all characters, locations, and props in the project and uses the actual @tags in the prompts it generates"; "Claude never triggers generation directly" | A |
| Moodboards | Up to 80 images, "around 10 high resolution reference images should generally be enough"; Soul 2.0 "learns the aesthetic register of that reference set and uses it to anchor your generations"; no training time is ever quoted, unlike Soul ID | B |
| Soul HEX / Color Transfer | Extracts a reference's dominant palette and applies it; built-in palettes available | B |
| Start and End Frames (May 2025) | Two images, "over 80 existing animation styles" between them | B |
| Popcorn | Storyboard and keyframe generator producing consistent frames | B |
| Elements | See section 7 | A |
| Canvas | Node graph; every model is a node; Soul IDs, products, brand references and prior generations drop in as nodes; templates; Figma-style multiplayer; credits only on node execution | A |
| Soul API style controls | `style_id`, `style_strength`, `custom_reference_id`, `custom_reference_strength` | A |

Whether camera body and lens choices are true model conditioning or prompt templating is not disclosed. Because the same controls are applied to closed third-party models with no lens inputs, the cross-model path is almost certainly templating; whether Soul Cinema and DoP receive native optics conditioning is unknown (C).

### Replication spec

**5.1 Preset records.** Each preset is data, not a prompt string:
```
Preset {id, name, category, preview_url, supports_start_end_frame,
        camera_traj: [{t, R, T, fov}] over N normalized frames,
        subject_motion_hint: "freeze"|"slowmo"|"natural",
        prompt_suffix_by_model: {seedance: "...", kling: "...", veo: "..."},
        native_control_by_model: {kling: "camera_control.orbit", ...}}
```
DoP consumes `camera_traj` directly (section 8). Licensed models get `native_control_by_model` when it exists, else `prompt_suffix_by_model`, plus keyframes rendered from a monocular 3D proxy when the model supports start and end frames.

**5.2 Optics controls.** Store bodies and lenses as records with a colour-science LUT, grain profile, halation and bloom parameters, distortion and bokeh descriptors, and a text descriptor. Apply in two places: (a) descriptor text into the enhanced prompt for every model; (b) for in-house models, scalar conditions `log(focal_mm)`, `sensor_size`, `f_stop` fed through adaLN alongside the timestep, trained with EXIF labels for stills and VLM estimates for video with 30% dropout. Film-stock looks are post LUT plus grain; no need to condition the model.

**5.3 Moodboards.** Zero-shot: SigLIP-encode up to 80 images, attention-pool into 16 style tokens, inject via IP-Adapter-style decoupled cross-attention into Soul. Optional background style-LoRA (rank 16, ~1000 steps) for premium boards. Expose `style_id` and `style_strength` exactly as Higgsfield's API does.

**5.4 Palette transfer.** k-means in CIELAB to a 5 to 8 colour palette; inject as named colours in the prompt and as a small palette-conditioning MLP trained by pairing images with their own palettes; post-hoc LAB histogram match as a fallback.

**5.5 Start and end frames, Popcorn.** Keyframe conditioning is native in Wan/Kling/Seedance; Popcorn is Soul plus Elements generating a consistent frame set from a shot list.

**5.6 Canvas.** React Flow DAG with typed ports (image, video, text, element, audio); JSON templates with declared input slots; Yjs CRDT for multiplayer; topological execution with batching of independent nodes.

---

## 6. Identity: Soul ID, Face Swap, Animate, Recast, Character Swap

### Evidence

**Soul ID (A):**
- Two variants in the official CLI: `--soul-2` (image) and `--soul-cinematic` (video/cinematic); consumed by `text2image_soul_v2` and `soul_cinematic`. Training returns a `reference_id` passed as `--soul-id`. Paid plan required.
- Photo count: the CLI skill says "Minimum 5, maximum 20. 8–12 is the sweet spot"; the web UI recommends 20 to 80 with at least one full-height photo. Training "about three minutes" to "3 to 5 minutes" (help center), "about 10 minutes" (avatar page); CLI default timeout 30 min.
- Learns "facial structure, proportions, and features"; body proportions only if a full-body shot is included; "clothing is controlled through your prompts and presets rather than being part of the learned identity".
- One person per Soul ID: "for scenes with two or more consistent characters, use Elements."
- Not exportable. Higgsfield compares it to Stable Diffusion LoRA: "Soul ID gives most of that consistency with none of the pipeline."
- Carries into video only as an image: generate a Soul ID still, save it as an Element, then the video model receives it as a reference image (Seedance `@imageN`, Kling `@elements`). No video model is fine-tuned.
- Documented conflict: one Aug 2026 help article says each Soul model has its own Soul ID; another says it is shared across the family.
- Drift, in Higgsfield's own words: "extreme style shifts or unusual angles can still introduce small drift"; "unmistakably the same person, not a pixel-identical face"; "tracks your reference photos rather than your current self". Third-party tests: strongest on close and mid shots; casting a real person into Kling motion control "returns a lookalike actor".

**Reference-image anchoring (A):** a single reference "anchors to that specific image at that specific angle in that specific lighting" and drifts when the scene changes. Higgsfield presents Soul ID as the fix.

**Face Swap (B):** image and video; one face per operation; with multiple faces "the AI will almost always prioritize the closest one"; 30 s to 2 min; free tier capped at 5 image swaps a day, video behind paywall. The engine is described only as an "optimized AI face swap engine"; no vendor attribution anywhere.

**Animate and Recast (A):** "Higgsfield ANIMATE powered by WAN 2.2" with two modes, character replacement and video motion transfer. Replace mode "swaps the character in the video with your uploaded Soul ID or trained image, keeping pose, pacing, and performance". Recast adds instant voice cloning, six-language dubbing with gender change preserving intonation, green-screen background replacement, and 30+ preset characters. Tips from Higgsfield's engineer: textured backgrounds beat pure white because the model uses background depth cues for shadows, edges and reflections.

**Character Swap 2.0 (B):** shipped "through a partnership with Kling" on Kling O1, a unified video model with motion transfer, for near-photoreal swaps in video and images.

**Voice (A):** Higgsfield Audio bundles ElevenLabs (default), MiniMax, Seed Speech and Vibe Voice, 74+ languages. An in-house, open-source `soul-voice-service` does voice design, cloning and direction on a "Breeze backbone, tokenizer and Qwen audio codec".

**Lipsync (B):** Lip-Sync Studio bundles Speak v2 (in-house), Sync Labs lipsync-2, InfiniteTalk, Kling AI Avatar (1080p/48fps in about a minute), Kling Lipsync, Veo 3.

### Replication spec

**6.1 Soul ID (per-identity fine-tune).**
- Preprocess: RetinaFace detect, align, reject blur (Laplacian variance), reject duplicates and occlusions, reject group photos (more than one large face). Caption each photo with a trigger token `<sks>` plus wardrobe and background text so the model does not memorize clothes (this matches Higgsfield's "clothing is controlled through prompts").
- Train a rank-32 LoRA on attention and FFN projections of the Soul DiT plus a learned identity token, 600 to 1200 steps, batch 4, lr 1e-4, prior-preservation with base-model "a person" renders. Precompute latents at upload. On one H100 this is 3 to 5 minutes; accept 5 to 80 photos.
- Train two LoRAs per identity in the background: one against the Soul 2.0 checkpoint, one against Soul Cinema. This reproduces the two-variant CLI and explains Higgsfield's conflicting "shared vs per-model" docs.
- Quality gate: render 8 test images; mean ArcFace cosine to uploads must exceed 0.55, else continue 300 steps or request more photos.
- Keep an ArcFace-conditioned identity adapter (PuLID-style) active at low weight during Soul ID generation for robustness under extreme style prompts.
- Store server-side only; return a `reference_id`.

**6.2 Elements and multi-character.** For two or more consistent people, render each Soul ID separately into canonical views and bind each as an Element; compose via multi-reference slots (Seedance takes up to 9 images) with `@tag` prompts. Do not attempt to merge LoRAs.

**6.3 Zero-shot identity in video (for DoP and Soul Cinema).** Stand-In architecture on the Wan backbone: VAE-encode the reference face as a one-frame latent, patchify with the video patchifier, concatenate tokens in every DiT block; rank-128 LoRA on q/k/v for face tokens only; restricted self-attention (face tokens attend to themselves, video tokens to both); RoPE for face tokens at frame 0 with height and width offsets past the video extent. About 1% extra parameters. Train on ~1M same-identity clip pairs.

**6.4 Face swap.** Two tiers.
- Fast: RetinaFace plus ByteTrack; pick the largest track (the "closest face" rule); 5-point align; inswapper_128 plus CodeFormer at 0.5; face-parsing mask (BiSeNet); per-frame LAB colour match; Poisson blend; flow-warped 20% temporal blend. 30 s for 5 s of video.
- Quality: identity-conditioned masked latent inpainting in the video DiT (Stand-In face-swap mode): dilate the face mask by 10 latent pixels, denoising strength 0.5 to 0.7, replace latents outside the mask with noised originals at every step. Preserves lighting and camera exactly.

**6.5 Animate / Recast.** Deploy Wan 2.2-Animate (open weights) in replace and motion-transfer modes: DWPose skeleton plus facial motion from the driving video, reference character image, relighting LoRA for scene matching, mask-and-composite to keep the original background and camera. Cap at 720p and 15 s per job. Voice: speaker-embedding TTS (F5-TTS / CosyVoice, or license ElevenLabs), LLM translation, forced alignment for timing, LatentSync or MuseTalk lip resync. Surface Higgsfield's reference tips in the UI: full body visible, textured background, matching lighting.

**6.6 Character swap 2.0.** License Kling O1 (as Higgsfield did) or, self-hosted, use Wan 2.2-Animate replace mode plus the zero-shot identity adapter for a second pass on the face.

**6.7 Lipsync.** Bundle one in-house model (LatentSync-class fine-tune on talking-head data) with licensed Sync Labs and Kling Avatar. Expose as `/v1/speak/{engine}`.

---

## 7. Elements, the AI Director and Supercomputer (the "reference anchor" system)

### Evidence

- **"Reference anchor" is a workflow name, not a product (A).** It appears only in a third-party Medium post and on Higgsfield's auto-generated SEO subdomain: "Reference Anchor workflow powered by SOUL ID. By training a model with 20 or more photos of a subject and locking a generated static frame as your reference, the video engine inherits the exact facial geometry and wardrobe." The workflow is: train a Soul ID, generate a hero frame, save it as an Element, and reference it in every subsequent generation.
- **Elements (A).** "An Element (a character, location, or prop) is created once and reused across shots and projects." Invoked with `@name` tags in prompts. The picker has source tabs (Uploads, Image Generations, Video Generations, Elements, Liked) and categories (Pinned, Shared, Characters, Locations, Props). Elements carry into Cinema Studio, Marketing Studio, Supercomputer, Canvas, Seedance 2.0 and Kling 3.0.
- **Native reference limits per model (A, from `higgsfield-ai/cli` MODELS.md).**

| Model | Images | Videos | Audio | Notes |
|---|---|---|---|---|
| Seedance 2.0 / 2.0 Mini | up to 9 (counting start/end) | 3 | 3 | max 12 files; `@image1`, `@video1` syntax; "the model treats it as a generation constraint" |
| Seedance 2.5 | 30 | 10 | 10 | modes t2v, omni_reference, video_edit, video_extension; in-prompt first/last frame and multi-keyframe |
| Kling 3.0 | start/end | | | multi-shot mode has an `@elements` input for a character, product or object |
| Veo 3.1 | API: start image only; UI: 1 to 3 references | | | |
| Cinematic Studio 3.0 API | max 15 across images, start/end, videos | | | |
| Cinema Studio 4.0 | up to 50 | | | runs on Seedance 2.5 |
| Soul | `soul-id`, `custom_reference_id` + `custom_reference_strength` | | | |

- **The AI Director is Claude (A).** "Claude Chat is the AI director built into Cinema Studio 3.5. It adjusts Genre, Style, and Camera settings through conversation and the setting panels update in real time." Persona "Mr. Higgs": "a built-in AI co-director that understands your project — characters, locations, style, and camera settings. Describe a scene in plain language and he'll break it into shots, adjust settings, and populate your prompt." "Claude-generated prompts go into the prompt box for your review. Claude never triggers generation directly."
- **Supercomputer (launched May 14, 2026) (A/B).** "Users send a single brief and Supercomputer plans the work, picks the right models, generates the assets." Higgsfield's engineering post "Inside Higgsfield #2: How We Built Supercomputer" describes "three layers of memory", "40+ built-in tools", "visual memory, model routing and human-authored Skills". Third-party reports (B) say the brain is a "Hermes Agent", a custom orchestration model built on Nous Research's Hermes 3 and fine-tuned for function calling and recursive tool use, which routes among Claude Opus 4.7, GPT-5.5 Pro, Gemini 3.1 Pro and the video models; users can pin a model or let the agent route. Supercomputer also hosts user-built apps (e.g. "LayerLab", which won a Higgsfield app contest).
- **Earlier orchestration (B).** SaaStr: the ad workflow "orchestrates existing models, Sora 2, GPT-4.1, and others, through a workflow engine that turns a product link or text prompt into a cinematic video ad". OpenAI case study: GPT-class models used for "Take my top-performing ad and generate 100 new variations".
- **Skills (A).** `higgsfield-ai/skills` on GitHub: human-authored skill files (Soul ID photo guide, Cinema Studio, product photoshoot with "backend prompt enhancement") consumed by the CLI, MCP and the agent.
- **No per-reference weight** is documented for Elements in video models; Soul exposes `custom_reference_strength` only.
- **How Elements map into native slots is undocumented (C).** The observable behaviour (Elements appear in Seedance prompts as `@imageN`, in Kling as `@elements`) implies server-side resolution of each `@tag` into the model's reference inputs plus a rewritten prompt.

### Replication spec

**7.1 Element registry**
```
Element {
  id, owner, kind: "character"|"location"|"prop"|"style",
  tag: "@name", pinned, shared_with[],
  canonical_images[]: {url, view: front|three_quarter|profile|full_body|detail, lighting: neutral},
  identity?: {soul_id_lora_ids[], arcface_emb[512]}, clip_emb[1024],
  text_descriptor: string   // VLM-written, deterministic
}
```
On creation, auto-render missing canonical views (character: front, three-quarter, profile, full body under neutral light using Soul plus the Soul ID LoRA; prop: three angles via Nano Banana Pro or Soul multi-view). This is the fix for "anchors to that specific angle".

**7.2 Tag resolver.** For each generation, parse `@tags`, then per target model:
- Seedance: pick the canonical view whose angle best matches the shot's camera; fill `@imageN` slots in reference priority order (subject, product, location, style) up to the model's limit; rewrite the prompt to reference `@imageN`.
- Kling: attach to the `elements` input; rewrite prompt to `@element-name`.
- Veo: up to 3 references, subject first.
- Soul / DoP / Soul Cinema: Soul ID LoRA plus the zero-shot identity adapter (6.3); start frame from a Soul render.
- Models with no reference slot: inject a Soul-rendered start frame.
Always merge each Element's `text_descriptor` into the prompt so text and image conditioning agree; disagreement is the main cause of drift.

**7.3 AI Director (Cinema Studio).** A Claude chat agent with read access to the project's Elements and settings and tools `set_setting(genre|style|camera_body|lens|focal|aperture|motion|speed_ramp)`, `draft_shot_list(script)`, `write_prompt(shot)`. It writes into the prompt box and settings panels and never calls generate; the user presses generate. Prompts it writes must use real `@tags` from the registry.

**7.4 Supercomputer-class agent.**
- **Router model.** A small function-calling model (Hermes 3 8B or 70B fine-tune, or Qwen3) trained on traces of `brief -> plan -> tool calls`, distilled from a frontier model; it delegates reasoning-heavy steps to a frontier LLM (Claude, GPT, Gemini) and generation to model tools. Users may pin a model.
- **Tools (40+).** Every generation endpoint, Element CRUD, Soul ID training, upscale, relight, layers, lipsync, dubbing, Canvas graph build and run, asset search, brand-kit read, ad-metrics read, app publish.
- **Memory, three layers.** (1) Conversation working memory; (2) project memory: Elements, brand kit, style choices, prior outputs and their scores; (3) visual memory: an embedding index (SigLIP + CLIP) over every asset the user has made or uploaded, queried by text and image for "make more like this".
- **Skills.** Markdown skill files (as in `higgsfield-ai/skills`) loaded by task type, encoding house workflows: product photoshoot, UGC ad, character sheet, storyboard. Human-authored, versioned, shared across CLI, MCP and agent.
- **Closed-loop QA.** After each generation: ArcFace cosine for characters, CLIP similarity for props and styles, VLM check of the shot description; on failure, retry with higher reference priority, a different canonical view, or a different model in the family, at most twice; then surface to the user. This loop is what makes the system appear to "reason about anchors".
- **Cost governor.** Plan first, show a credit estimate, generate only on approval; free to plan, credits on execution (Canvas already works this way).

**7.5 Multi-shot continuity.** Per-project scene state (location Element, lighting descriptor, palette, last frame per shot). Consecutive shots receive the previous last frame as start frame, or for DoP use clip-to-clip continuation (section 8).

---

## 8. Higgsfield DoP (Director of Photography)

### Evidence (A unless noted)

- DoP I2V-01-preview launched March 31, 2025 as Higgsfield's own image-to-video model. The 3-vote check refuted the reading that DoP is merely a preset layer over licensed models: the help center calls it "Higgsfield's native image-to-video model", it is benchmarked as "a proprietary Image-to-Video (I2V) model" on AMD MI300X, and it is resold as a standalone model by Segmind, WaveSpeed and ComfyUI Cloud.
- Architecture statement: "a novel architecture that blends diffusion models with reinforcement learning"; "applied reinforcement learning after diffusion, inspired by how DeepSeek trained LLMs to reason, but instead taught the model camera movement, lighting, lensing, and scene structure". No parameter count, backbone, resolution, fps, dataset or reward design has ever been disclosed. The CTO's background is deep RL (author of the `higgsfield` orchestration framework and RL tutorials), which is the plausible origin of this design (C).
- Control surface from the official JS SDK: endpoint `/v1/image2video/dop`; `model ∈ {dop-lite ("basic speed and quality"), dop-turbo ("2x speed with priority queue"), dop-standard ("highest quality with priority queue", formerly "preview")}`; `prompt`; `input_images` (one image); optional `input_image_end_url`; `motions: [{id, strength}]` with strength clamped to 0 to 1, default 1.0 (third parties recommend 0.3 to 1.0); `seed` 0 to 1,000,000; `enhance_prompt` default true; webhooks. No user-facing duration, resolution, fps or aspect: output is fixed server-side, about 5 s at 720p-class, billed per 3-second segment. Motions are fetched via `getMotions()` and each carries `{id, name, description, preview_url, start_end_frame}`; categories Effects, Basic Camera Control, Epic Camera Control; 50 to 100+ entries.
- Credits: DoP Lite 5, Turbo 16, Preview/Standard 23. Turbo: "1.5x faster processing and 30% lower cost compared to the standard model". Third-party API prices from $0.125 (WaveSpeed) to $0.86 (Segmind) per video.
- No "DoP 2" exists. Cinema Studio is an orchestration and prompting layer over third-party engines, not a new in-house video model (B). "Higgsfield Standard" is the `dop-standard` tier.
- Reviews (B): DoP "provided granular control over camera dynamics not seen in Runway or Pika" (Curious Refuge) but Kling "handles smooth, controlled camera movement better" (InnoBotZ) and "first 3 attempts producing awkward motion" (Dynalord). No quantitative camera-trajectory benchmark of DoP exists.

### Published methods this maps onto

| Method | Contribution | Openness |
|---|---|---|
| CameraCtrl (2024) | Per-pixel Plücker ray embeddings from extrinsics and intrinsics, multi-scale camera encoder injected into temporal attention of a frozen video diffusion model; RealEstate10K; two-stage (domain LoRA, then camera module); presets are stored pose files | Code and weights |
| MotionCtrl (SIGGRAPH 2024) | Decoupled camera module (RT matrices appended to temporal self-attention) and object-trajectory module; plug-in on LVDM, SVD, AnimateDiff | Code and weights |
| CameraCtrl II (ICCV 2025, ByteDance Seed) | DiT-era lightweight camera injection that preserves dynamics; purpose-built high-dynamics camera-annotated dataset; autoregressive clip-to-clip exploration; about 5x more scene motion and 2x lower pose error than CameraCtrl v1 | Paper only |
| ReCamMaster (ICCV 2025 oral, Kuaishou) | Source-video tokens concatenated with target tokens along the frame axis; MultiCamVideo: 13.6K UE5 dynamic scenes × 10 synchronized cameras = 136K videos at 1280², 81 frames; Pan/Tilt, Translation, Arc, Random, Static trajectories | Code, Wan 2.1 weights, dataset |
| Seaweed-APT2 (ByteDance) | Relative-to-previous-frame Plücker coordinates to stop unbounded growth on long moves; unit-variance scaling; random init of the new input projection | Paper |

### Replication spec

**8.1 Backbone.** Wan 2.2 14B I2V, or the human-centric continued pre-train from 4.2. Image conditioning via the native first-frame latent path; optional end-frame conditioning via last-frame latent concatenation with a mask channel (this reproduces `input_image_end_url` and the `start_end_frame` flag on presets).

**8.2 Camera conditioning (CameraCtrl II recipe).**
- Each preset stores per-frame `[R|t]` and `K` at the latent frame rate; `strength` scales the trajectory magnitude (translation and rotation deltas multiplied by strength, 0 = static camera).
- Compute per-pixel Plücker coordinates `(d, o × d)` per latent frame, relative to the previous frame, scaled to unit standard deviation.
- Patchify the 6-channel Plücker map with the video's 3D patchifier; add to visual token embeddings through a small-random-initialized projection (a few million parameters).
- Train the DiT unfrozen at lr 1e-5 and the projection at 1e-4 so dynamics are preserved; freezing the DiT (CameraCtrl v1) collapses scene motion.
- Add MotionCtrl-style sparse point-track heatmaps as a second optional channel for subject-locked presets (head tracking, push-to-glass).
- Feed optics scalars (focal, aperture) via adaLN as in 5.2 so "lensing" is learned, matching Higgsfield's claim.

**8.3 Data.**
1. Real clips with VGGSfM/MegaSaM trajectories from the 4.1 corpus, filtered to low reprojection error and substantial subject motion.
2. Synthetic paired data: extend MultiCamVideo in Unreal Engine 5 with MetaHuman actors and the exact preset trajectories (crash zoom, dolly zoom with co-varying focal and distance, 360 orbit, bullet time with frozen actors, robo-arm arcs, FPV, jib, 360 roll). Target 20K scenes × 10 cameras.
3. Effects presets (the "Effects" category: explosions, disintegration, etc.) are trained as text-conditioned styles on VFX clip collections, not camera paths.

**8.4 RL post-training.**
- Rewards on sampled clips: camera accuracy (VGGSfM on the output, aligned to the target path; negative translation and rotation error); dynamics preservation (RAFT foreground flow inside a target band); geometric consistency (VGGSfM success and reprojection error); realism and cinematic preference (the 4.2 reward model plus 20k human pairs judged specifically on camera moves); identity preservation (ArcFace cosine between input image and output frames).
- Algorithm: Flow-GRPO or DanceGRPO, 8 samples per (image, preset) group, KL penalty to the supervised checkpoint, 2k to 5k steps at 480p, verify at 720p.

**8.5 Continuation.** ReCamMaster-style conditioning on the previous clip's tokens for long moves and multi-shot scenes.

**8.6 Serving tiers.** Standard: full model, 50 steps, priority queue. Turbo: 8-step DMD2 or self-forcing distillation (1.5 to 2x faster, 30% cheaper). Lite: fewer frames and 480p. FP8 on MI300X or H100; fixed 5 s output; bill per 3 s segment.

**8.7 Fallback for licensed models.** Each preset carries `native_control_by_model` and `prompt_suffix_by_model`; for models with keyframes, render start and end frames from a Depth Anything V2 point-cloud reprojection of the input image along the trajectory.

---

## 9. Layers, Relight, Generative Fill, Color Palette

### Evidence

- **Higgsfield Layers (A; formerly "EditLayers", released around Aug 11, 2026).** "A layer-based photo editor" with "Layer Separation, Edit Text, Regional Edit, Relight, Remove BG, and 4K/8K Upscale"; launch line: "layer decomposition, flawless text rendering, and native 4K". Layer Decomposition options: resolution 1K / 1.5K / 2K, mode Standard or Fast, layer count (5 by default, adjustable). Costs 15 credits. Output: "a clean background plate, isolated subject, and lifted text — each downloadable as a PNG with the original framing preserved"; Remove BG yields "transparent alpha". No PSD export. The decomposition engine is not attributed. Image only; no evidence of video layers. Exposed as a platform primitive (a community "LayerLab" app on Supercomputer reuses it).
- **Generative fill (A).** "Nano Banana Pro Inpaint... You paint over any object - and the model transforms only what you highlighted"; on Layers "the Nano Banana Pro engine generates new objects with correct perspective and lighting". An in-house "SOUL Inpaint" also exists. Per-edit model menu: "Nano Banana Pro is best for brush edits and object swaps, Seedream for ultra-realistic photo edits, and FLUX or GPT Image for precise, prompt-led changes."
- **Edit Text (B).** "Runs Detect text first, listing every line found on the image, before generating the replacement." Engine unnamed, most likely Nano Banana Pro given its text-rendering claims (C).
- **Relight, image (A).** "A 3D directional pad lets the user redefine the light source and color temperature", "granular brightness slider", "specific hex-code color input", "six rapid-fire presets: Top, Front, Right, Left, Back, and Bottom"; "leveraging advanced generative AI and depth-mapping technology to manipulate light sources in a 3D space". Released around Jan 2026.
- **Relight and Color Palette, video (A).** Standalone since Cinema Studio 4.0: lighting "offers 6 presets [Silhouette, Practicals, Window, Overhead Fall, Contre-jour, Soft], or a custom setup with control over color, brightness, diffusion, and angle"; a "2-source Video Lighting Console". Implemented as a generative re-render ("generate a new version based on the existing footage"). No named method; IC-Light is never mentioned.
- Known complaints (B): queue waits under load; "quality may degrade noticeably if multiple edits are applied in sequence".

### Replication spec

**9.1 Layer decomposition**
1. Parse: SAM 2 automatic masks merged with Grounding DINO labels; rank instances by area and saliency; cap at N (default 5): background, primary subject, secondary subjects, occluders, text.
2. Text: PaddleOCR detect and recognize; text layer lifted as its own PNG; Edit Text re-typesets via a layout-conditioned text renderer (AnyText / GlyphControl) or a Nano Banana Pro call with the detected lines as the edit instruction.
3. Amodal completion per subject (Pix2Gestalt-style amodal mask plus a diffusion inpainter conditioned on the visible region) so layers can be moved without holes.
4. Background plate: remove all foreground masks and inpaint with LaMa (Fast) or a diffusion inpainter (Standard) at 1K / 1.5K / 2K.
5. Matting: ViTMatte on a SAM-derived trimap for hair and soft edges.
6. Export ordered RGBA PNGs at the original framing, plus a Depth Anything V2 depth map for 2.5D placement in Canvas. Add PSD export as a differentiator (Higgsfield lacks it).
Latency: Fast about 3 s at 1K, Standard about 20 s at 2K.

**9.2 Relight (image).** Depth Anything V2 depth, normals from depth (or StableNormal). Foreground relight with IC-Light conditioned on a rendered light map: directional pad sets the light vector over the normal field; brightness scales the map; hex colour or colour temperature tints it; softness sets Gaussian blur of the map; six presets are canned light vectors. Shadow synthesis: project the subject alpha along the light vector using depth onto the background plate; blur by softness. Harmonize with a harmonization net.

**9.3 Relight (video, two sources).** Same light-map construction with two light sources summed; per-frame IC-Light with the same maps, then flow-warped temporal smoothing; premium tier uses a video relighting model (Light-A-Video class) or a diffusion re-render conditioned on the original clip, which is what Higgsfield's "generate a new version based on the existing footage" implies. Presets (Silhouette, Practicals, Window, Overhead Fall, Contre-jour, Soft) are stored light-map templates.

**9.4 Color Palette (video).** Palette extraction as in 5.4; apply as a 3D LUT fitted by histogram matching in LAB with a temporal lock; optional diffusion re-grade for the premium tier.

**9.5 Generative fill.** Default: call the licensed editor (Gemini image / Nano Banana Pro) with mask and instruction; self-hosted: FLUX.1 Fill or Qwen-Image-Edit; in-house: Soul Inpaint (Soul fine-tuned with mask channel). Per-edit model menu, exactly as Higgsfield exposes it.

---

## 10. Audio

Evidence (A/B): Seed Audio 1.0 (ByteDance) as the all-in-one dialogue, ambience, music and effects model; ElevenLabs default for TTS and cloning with MiniMax, Seed Speech and Vibe Voice as alternatives; in-house open-source Soul Voice; `text2speech_v2` in the web client; Lip-Sync Studio as in 6.

Replication: license ElevenLabs and Seed Audio; self-host an open TTS with cloning (CosyVoice or F5-TTS) as the in-house tier; LLM translation plus forced alignment for dubbing; lipsync per 6.7.

---

## 11. Data, training and cost plan

| Component | Base | Data | Compute (order of magnitude) |
|---|---|---|---|
| Soul image family | FLUX-class DiT | 100M+ captioned fashion/portrait/editorial images; art-director preference pairs | 2k to 5k H100-days |
| Soul ID | Soul + rank-32 LoRA per identity per variant | user uploads | 1 H100 × 3 to 5 min per identity |
| Identity adapters | Stand-In on Wan; PuLID on Soul | 1M identity-paired clips; 2M face images | 100 to 300 H100-days |
| Video base | Wan 2.2 14B | 10 to 50M human-centric clips, VLM-captioned, SfM-labelled | 5k to 20k H100-days |
| DoP camera module + RL | above | real SfM clips + 200K UE5 synthetic videos + VFX clip set | 300 to 1k H100-days |
| Layers / relight | SAM 2, LaMa, IC-Light, Depth Anything V2, ViTMatte | mostly pre-trained; fine-tune inpainter on product/fashion | under 50 H100-days |
| Router model | Hermes 3 / Qwen3 8B to 70B | 100k distilled agent traces | 20 to 100 H100-days |
| Captioner | Gemini API or Qwen2.5-VL 72B | | inference only; the largest single line item at 10M+ clips |

Higgsfield's own path was cheaper than this table implies for video: it licenses Seedance, Kling and Veo for most pixels and reserves in-house training for Soul, DoP and identity.

---

## 12. Serving and infrastructure

- Training on Google Cloud (A3 H100 / TPU v5p) as Higgsfield did, or any H100/B200 cluster (Nebius).
- Inference pools per model class: DoP and Wan-based identity models on MI300X or H100 with FP8 and distilled checkpoints; Soul on L40S/H100 at about 2 s per image; licensed models behind adapters with per-vendor concurrency.
- Asset store with full lineage for Canvas re-runs and visual memory.
- Safety: consent attestation for Soul ID and face swap; NSFW and public-figure classifiers on identity uploads; C2PA manifests; the `NSFW` job status.
- Distribution: web, REST API, CLI, MCP server, Figma plugin, and a hosted app platform (Supercomputer apps) so third parties build on the primitives.

---

## 13. Product surface to match

| Feature | Section |
|---|---|
| Model picker by family, 50+ models, one credit pool | 3 |
| REST API in the fal endpoint convention, SDKs, CLI, MCP | 3 |
| Prompt enhancer on by default | 4.4 |
| DoP presets with strength, start/end frame, Lite/Turbo/Standard | 8 |
| Cinema Studio: bodies, lenses, focal, aperture, motion, speed ramps, Claude director | 5, 7.3 |
| Elements with @tags across all models | 7 |
| Supercomputer agent with skills, memory, routing, hosted apps | 7.4 |
| Soul ID: 5 to 80 photos, minutes, two variants | 6.1 |
| Moodboards, Soul HEX, Popcorn, Start and End Frames | 5 |
| Canvas: node graph, templates, multiplayer | 5.6 |
| Layers, Relight (image and video), Color Palette, Edit Text, Remove BG, Generative Fill | 9 |
| Face Swap, Animate, Recast, Character Swap 2.0 | 6.4 to 6.6 |
| Upscale (two engines), Skin Enhancer, deflicker | 4.5 |
| Higgsfield Audio, Lip-Sync Studio, dubbing | 10 |

---

## 14. Confidence summary

| Claim | Grade |
|---|---|
| Higgsfield licenses 50+ models and routes video to Seedance/Kling/Veo/Sora/Wan; DoP layered on top | A (verified) |
| Soul is Higgsfield's own image model; Soul ID is a train-once identity | A (verified) |
| DoP is a proprietary i2v model with diffusion plus RL post-training, exposed via presets with strength 0 to 1, fixed ~5 s output, three tiers | A (verified; "only a layer" reading refuted; SDK confirms control surface) |
| API scheme, auth, parameters, statuses, retries | A (official SDK source) |
| Elements are @-taggable characters/locations/props reused across models; per-model reference limits as tabulated | A (official CLI docs) |
| Cinema Studio AI Director is a Claude chat that drafts settings and prompts but never triggers generation | A |
| Supercomputer is an agent with routing, 40+ tools, three memory layers and human-authored skills | A (first-party) |
| Supercomputer's router is a Hermes 3 fine-tune orchestrating Claude/GPT/Gemini | B (third-party only) |
| Animate/Recast run on WAN 2.2-Animate; Character Swap 2.0 on Kling O1 | A / B |
| Upscale uses Topaz and a ByteDance engine; generative fill uses Nano Banana Pro; ElevenLabs is the default voice | A |
| Gemini used for captioning and control; in-house model scoped to people, faces, camera, lighting; trained on GCP | A |
| Layers: 5-layer default, 1K to 2K, Standard/Fast, PNG export, 15 credits; Relight has a 3D pad, six presets and is depth-map based | A/B |
| Cinema Studio camera/lens enumerations | B (third-party reverse engineering) |
| Moodboards are zero-shot conditioning rather than training | C |
| Soul ID is a LoRA-style fine-tune | C (strong inference) |
| DoP uses Plücker-style camera conditioning | C (no architecture disclosed) |
| Elements resolve server-side into native reference slots | C (observed behaviour) |
| "Reference anchor" is a workflow term, not a product | A |
| Face Swap engine | unknown |
| Funding, valuation and revenue figures | B |

---

## 15. Sources

First-party (Higgsfield):
- https://github.com/higgsfield-ai/higgsfield-js (SDK source: DoP tiers, motions, parameters)
- https://github.com/higgsfield-ai/cli and its MODELS.md (per-model reference limits, `enhance_prompt`)
- https://github.com/higgsfield-ai/skills (Soul ID photo guide, Cinema Studio and product-photoshoot skills)
- https://github.com/higgsfield-ai/soul-voice-service
- https://github.com/higgsfield-ai/higgsfield (CTO's GPU orchestration framework)
- https://pypi.org/project/higgsfield-client/
- https://docs.higgsfield.ai/docs/authentication ; https://docs.higgsfield.ai/docs/help/faq ; https://open.higgsfield.ai/pricing
- https://higgsfield.ai/creator-hub/help-center/ai-models/which-ai-model-should-i-use
- https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-dop
- https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-create-and-use-a-soul-id-character
- https://higgsfield.ai/creator-hub/help-center/tools/how-do-i-use-cinema-studio
- https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-lipsync-voiceover-and-aspect-ratios
- https://higgsfield.ai/creator-hub/changelog
- https://higgsfield.ai/blog/Introducing-Higgsfield-DoP-preview
- https://higgsfield.ai/blog/AMD-and-Higgsfield-DoP-TensorWave
- https://higgsfield.ai/blog/Higgsfield-Fastest-Model-Yet-Introducing-Turbo
- https://higgsfield.ai/blog/how-we-built-cinema-studio ; https://higgsfield.ai/blog/cinema-studio-guide ; https://higgsfield.ai/blog/cinema-studio-3.5-full-tutorial ; https://higgsfield.ai/blog/cinema-studio-4-0
- https://higgsfield.ai/cinema-studio ; https://higgsfield.ai/cinematic-video-generator ; https://higgsfield.ai/generate/elements
- https://higgsfield.ai/supercomputer-intro ; https://higgsfield.ai/blog/how-we-built-supercomputer
- https://higgsfield.ai/blog/Why-Does-Your-AI-Characters-Face-Keep-Changing
- https://higgsfield.ai/blog/sould-id-best-character-consistency ; https://higgsfield.ai/blog/Soul-ID-AI-Character-Consistency
- https://higgsfield.ai/blog/AI-Face-Character-Swap-in-Video-Photo-PRO-Guide
- https://higgsfield.ai/blog/Higgsfield-Animate-WAN-2.2-Animate ; https://higgsfield.ai/flow/animate ; https://higgsfield.ai/recast-studio
- https://higgsfield.ai/blog/generating-with-seedance-2-0 ; https://higgsfield.ai/blog/seedance-2-0-pricing-2026
- https://higgsfield.ai/blog/create-custom-ai-moodboard-soul-2 ; https://higgsfield.ai/soul-intro
- https://higgsfield.ai/canvas-intro ; https://higgsfield.ai/camera-controls
- https://higgsfield.ai/higgsfield-layers ; https://higgsfield.ai/blog/edit-photos-with-ai-higgsfield ; https://higgsfield.ai/image-editing
- https://higgsfield.ai/blog/Top-Editing-Tool-in-2025-Nano-Banana-Pro-Inpaint ; https://higgsfield.ai/blog/Higgsfield-SOUL-Inpaint-Editing-with-AI-Realism
- https://higgsfield.ai/blog/Relight-Director-Style-Cinematic-Lighting ; https://higgsfield.ai/blog/video-relight-color-palette-higgsfield
- https://higgsfield.ai/ai-video-upscaler ; https://higgsfield.ai/voice-cloning ; https://higgsfield.ai/blog/make-ai-lipsync-videos
- https://higgsfield.ai/blog/credits-vs-unlimited-ai-video-generation ; https://higgsfield.ai/blog/higgsfield-api ; https://higgsfield.ai/higgsfield-api
- https://cloud.google.com/transform/3-lessons-for-gen-ai-startups-higgsfield-ai-infrastructure-talent-models
- https://www.topazlabs.com/learn/preserving-artistic-continuity-with-higgsfield-ai
- https://nebius.com/customer-stories/higgsfield-ai
- https://openai.com/index/higgsfield-from-prompt-to-production-with-astra/

Third-party reporting, reviews and reverse engineering:
- https://techcrunch.com/2026/08/17/higgsfield-raises-400m-series-b-quadrupling-its-valuation-in-8-months-to-5-4b/
- https://techcrunch.com/2024/04/03/ (Diffuse launch)
- https://en.wikipedia.org/wiki/Higgsfield_AI
- https://sacra.com/research/alex-mashrabov-higgsfield-ai-video-production/ ; https://sacra.com/c/higgsfield/
- https://www.saastr.com/500m-arr-60-engineers-cash-flow-positive-how-higgsfield-actually-runs-with-ceo-alex-mashrabov/
- https://menlovc.com/perspective/ (Higgsfield seed memo)
- https://github.com/OSideMedia/higgsfield-ai-prompt-skill (Cinema Studio enumerations)
- https://github.com/nukIeer/higgsfield-unlimited-mcp ; https://github.com/geopopos/geo_higgsfield_ai_mcp ; https://github.com/codeforstartups/higgsfield-docs ; https://github.com/jeremieLouvaert/ComfyUI-Higgsfield-Direct
- https://www.segmind.com/models/higgsfield-image2video/api ; https://wavespeed.ai/blog/posts/introducing-higgsfield-dop-image-to-video-on-wavespeedai/
- https://skybreakai.com/blog/higgsfield-models-explained-2026 ; https://aireiter.com/blog/higgsfield-ai-reviews-pricing-vs-api ; https://pollo.ai/hub/higgsfield-ai-review ; https://www.therundown.ai/tools/higgsfield
- https://perplexityaimagazine.com/ai-news/higgsfield-ai-character-swap-photorealistic-video/
- https://petapixel.com/2025/08/06/ (Topaz partnership) ; https://petapixel.com/2026/01/09/this-ai-app-lets-you-relight-your-photos/
- https://medium.com/@302.AI/higgsfield-soul-id-test-how-realistic-is-the-character-consistency-1bc8b3250bca ; https://wink.ai/blog/higgsfield-reviews
- https://kinomotomag.com/2025/05/05/higgsfields-new-start-end-frame-feature/
- https://layer.ai/vs/higgsfield ; https://www.media.io/image-effects/nano-banana-pro-higgsfield-review.html
- https://creatify.ai/blog/higgsfield-pricing-(2026)-plans-and-what-you-ll-actually-pay ; https://www.blotato.com/blog/higgsfield-pricing ; https://blog.segmind.com/higgsfield-credits-explained-expiry-rules-and-real-cost/
- https://www.wionews.com/world/is-unlimited-a-scam-higgsfield-is-making-customers-wait-for-days-to-generate-even-1-video-1787006158862 ; https://www.caimera.ai/blogs/higgsfield-ai-twitter-ban-case-study-how-platform-trust-collapses

Research:
- CameraCtrl, arXiv 2404.02101, https://github.com/hehao13/CameraCtrl
- CameraCtrl II, arXiv 2503.10592, ICCV 2025
- MotionCtrl, arXiv 2312.03641, https://github.com/TencentARC/MotionCtrl
- ReCamMaster, arXiv 2503.11647, MultiCamVideo dataset
- Seaweed-APT2, Autoregressive Adversarial Post-Training, Appendix G
- Stand-In, arXiv 2508.07901, CVPR 2026
- Concat-ID arXiv 2503.14151; MagicMirror arXiv 2501.03931; ConsisID; EchoVideo
- Wan 2.2-Animate (Alibaba), IC-Light (Zhang et al.), SAM 2, Depth Anything V2, ViTMatte, LaMa, Flow-GRPO, DanceGRPO
- InsightFace blog, March 2026 face swapping papers
