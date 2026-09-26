# Higgsfield AI: Research Report and Replication Spec

Date: 2026-09-26
Method: deep-research workflow (1 scoping agent, 5 search agents, 28 fetch agents, 7 verification votes), then manual synthesis. The run was stopped at 37 agents to respect a credit cap, so the adversarial verification phase covered only three central claims. Everything else is marked with an evidence grade.

Evidence grades used throughout:

| Grade | Meaning |
|---|---|
| **A** | Verified by 3-vote adversarial check, or stated on more than one first-party Higgsfield page and corroborated by an independent source |
| **B** | Stated by Higgsfield on one page (help center, blog, product page) or by one reputable third party; not independently verified |
| **C** | Plausible inference from B-grade facts plus published research; Higgsfield has not confirmed it |

A caveat on provenance: direct fetches of higgsfield.ai, arxiv.org, wikipedia.org and techcrunch.com were blocked by the sandbox egress proxy. Quotes from those domains were recovered from search-engine snippets of the same pages, or from the authors' GitHub repositories for the papers. Wording is consistent across multiple snippets but has not been checked against live HTML.

---

## 1. What Higgsfield actually is

Higgsfield is a two-layer product (grade A):

1. **An aggregator.** It licenses 15+ third-party image, video and audio models and sells them under one credit pool: Seedance 2.0 (ByteDance), Kling 3.0 (Kuaishou), Veo 3.1 (Google), Sora 2 (OpenAI), Wan 2.6/2.7 (Alibaba), Hailuo 2.3 (MiniMax), Nano Banana / Nano Banana Pro (Google Gemini image), GPT Image (OpenAI), Seed Audio (ByteDance). Its own help center routes users by task: "Seedance handles realistic motion and Kling handles longer or multi-shot clips, with Higgsfield DOP adding VFX and cinematic camera control."
2. **An in-house layer** that sits over those models and is the actual product moat:
   - **Soul** image model family (Soul, Soul 2.0, Soul Cinema), in-house.
   - **Soul ID**, a per-user trained identity that locks a face across generations.
   - **Soul HEX** (palette transfer) and **Moodboards** (multi-image aesthetic learning).
   - **Higgsfield DoP** (Director of Photography), a proprietary image-to-video model with 50 to 100+ named camera-move presets.
   - **Cinema Studio**, an optics-aware shot builder (camera body, lens, focal length) with an "AI Director".
   - **Canvas**, a node-graph multi-model orchestration editor.
   - **Layers**, ML image decomposition into editable layers, plus depth-aware relighting and generative fill.
   - **Face Swap / Character Swap ("Recast")**, video identity replacement.
   - A post-processing pipeline: 4K upscale, flicker stabilization, skin enhancement, relighting (grade B, from a third-party inventory).

The critics' "it's just a wrapper" framing is half right. Raw generation quality for most video comes from licensed models. What is not a wrapper is: DoP, Soul, Soul ID, the intent-capture UX (presets, moodboards, optics controls), the orchestration graph, and the data/captioning pipeline behind them.

### Company facts (grade B unless noted)

| Item | Value |
|---|---|
| Founded | 2023, by Alex Mashrabov (ex-Snap head of generative AI; sold AI Factory to Snap) |
| Series A | $50M, GFT Ventures, Sept 2025, $1B valuation; $80M extension led by Accel, Jan 2026, $1.3B |
| Series B | $400M, Aug 2026, led by DST Global with Goldman Sachs Alternatives, Valor, Tribe; $5.4B valuation |
| Revenue | ~$200M annualized end-2025; ~$700M annualized July 2026; $1B ARR target |
| Compute | Google Cloud Vertex AI / AI Hypercomputer for training (petabytes of video); Nebius AI and TensorWave (AMD MI300X) for DoP inference |
| Pricing | Subscription tiers roughly $15 to $129/mo plus credits; Seedance 2.0 "Enhanced Fast" sold as add-on; Soul ID training requires Basic tier or above |
| API | Public API exposing Soul, DoP presets, and routed third-party models; DoP also resold via Segmind, WaveSpeed, ComfyUI Cloud |
| Controversy | Feb 2026 criticism over marketing "unlimited" access to partner models |

Founder strategy, stated in a Google Cloud case study (grade A): build only the pieces where you can win in-house, license the rest. The in-house video model was scoped narrowly to "people being people": faces, expressions, dynamic camera and lighting.

---

## 2. System architecture (target for replication)

```
                    ┌──────────────────────────────────────────────┐
                    │  Web app / API / Canvas graph editor          │
                    └───────────────┬──────────────────────────────┘
                                    │ job spec (JSON)
                    ┌───────────────▼──────────────────────────────┐
                    │  Orchestrator ("AI Director")                 │
                    │  - LLM/VLM planner (shot list, prompt rewrite)│
                    │  - Reference registry (characters, products,  │
                    │    styles, Soul IDs, moodboards)              │
                    │  - Model router (family -> latest version)    │
                    │  - Credit metering                            │
                    └───┬───────────┬───────────┬──────────────┬───┘
                        │           │           │              │
              ┌─────────▼──┐  ┌─────▼─────┐ ┌───▼──────┐ ┌─────▼──────┐
              │ In-house   │  │ Licensed  │ │ Identity │ │ Edit stack │
              │ Soul (img) │  │ Seedance  │ │ Soul ID  │ │ Layers     │
              │ DoP (i2v)  │  │ Kling Veo │ │ Swap /   │ │ Relight    │
              │            │  │ Sora Wan  │ │ Recast   │ │ Gen fill   │
              └─────────┬──┘  └─────┬─────┘ └───┬──────┘ └─────┬──────┘
                        └───────────┴───────────┴──────────────┘
                                    │
                    ┌───────────────▼──────────────────────────────┐
                    │  Post-processing: upscale, deflicker,         │
                    │  skin enhance, relight, audio, mux            │
                    └──────────────────────────────────────────────┘
```

The remainder of this document specifies each box.

---

## 3. Subsystem: model router and aggregation layer

**Confirmed (A):** Users pick a model *family*, not a version; the platform routes to the latest version in the family and new versions become the default on launch. Canvas runs "every model on Higgsfield" as nodes and routes outputs between them. Credits are charged per node execution at the model's normal rate.

**Replication spec**

- Maintain a `ModelFamily` table: `{family, versions[], default_version, capabilities{t2i,i2i,t2v,i2v,v2v,ref_images_max,start_end_frame,audio,max_duration,resolutions}, cost_per_unit, provider_adapter}`.
- One provider adapter per vendor (ByteDance, Kuaishou, Google, OpenAI, Alibaba, MiniMax) normalizing to a common `GenerationRequest` (prompt, negative, references[], start_frame, end_frame, camera_spec, duration, fps, seed, aspect).
- Capability negotiation: the orchestrator inspects `capabilities` to decide how to inject references (native multi-reference for Seedance 2.0 and Kling 3.0, start-frame injection for models without reference slots).
- Queue and retry with vendor-specific rate limits; store every artifact with full lineage (parent node, model, version, prompt, seed) so Canvas graphs and saved templates are re-runnable.
- Credit ledger with reservation at submit and settlement at completion.

Nothing here is technically novel; the value is coverage and the normalization layer.

---

## 4. Subsystem: realism

### What Higgsfield does (evidence)

- **Narrow in-house foundation model (A).** The 2024 Google Cloud case study: in-house video model focused on "more life-like faces and expressions, dynamic camera movements and lighting", trained on petabytes of video on Vertex AI.
- **VLM captioning of training data (A).** Gemini is used "for video understanding and control over video generation, and video captioning with highly accurate captions that deliver 50% better matching than competitors." Dense, structured captions are the single biggest lever on prompt adherence and realism for a diffusion model.
- **Routing to the best licensed model for realism (A).** Seedance for human motion and expression realism; Kling for long or multi-shot clips.
- **Optics conditioning (B).** Cinema Studio: choosing a focal length "alters the physical characteristics of the generated virtual lens" (background compression, depth of field). Physics-aware motion and native audio.
- **Post-processing pipeline (B).** 4K upscale, flicker stabilization, skin enhancement, relighting.
- **Gemini-based prompt rewriting (C).** Not stated outright, but the Gemini "control over video generation" quote plus the AI Director strongly implies an LLM/VLM rewrites sparse user prompts into dense structured prompts before hitting any generator.

### Replication spec

**4.1 Data and captioning pipeline (the actual moat)**

1. Ingest licensed and scraped video, shot-segment with TransNetV2 or PySceneDetect, filter for humans present (face detector hit rate), motion magnitude (RAFT optical flow mean between percentile 20 and 95), aesthetic score (LAION aesthetic v2 above 5), and no burned-in text/watermarks (OCR).
2. Estimate per-clip camera trajectories with VGGSfM or MegaSaM; discard clips where SfM fails.
3. Caption every clip with a VLM (Gemini 2.x class, or Qwen2.5-VL 72B self-hosted) using a fixed schema:
   ```
   {subject, action, expression, wardrobe, environment, time_of_day,
    lighting{key,fill,rim,color_temp,quality}, camera{shot_size,angle,move,lens_mm,dof},
    style{film_stock,grade,era}, audio_hint, negative_traits}
   ```
   Also produce a natural-language paragraph rendered from the schema. Train the video model on both forms with random dropout of fields so it works with sparse prompts.
4. Deduplicate near-identical clips by CLIP/ViCLIP embedding cosine > 0.95.

Target: 10 to 50M clips of 2 to 10 s for a competitive DiT; Higgsfield's "petabytes" is consistent with this scale.

**4.2 Base video model**

Do not train from scratch. Start from an open DiT with a 3D causal VAE (Wan 2.2 14B or Wan 2.1 14B; HunyuanVideo is an alternative) and continue pre-training on the curated human-centric corpus at 480p then 720p then 1080p, with the structured captions. This matches what Higgsfield's founder describes as "post-training/fine-tuning" of open models rather than pure from-scratch training (Sacra interview, grade B).

Then apply preference post-training:
- Collect pairwise human preferences on realism (skin, hands, eyes, motion naturalness), roughly 50k pairs.
- Train a reward model (VideoAlign / VisionReward style, or a fine-tuned VLM scoring on the same schema).
- Run Flow-GRPO or DPO on the DiT with the realism reward. This is the same class of "diffusion + reinforcement learning" Higgsfield names for DoP.

**4.3 Prompt rewriter**

A VLM call before every generation:
- Inputs: user text, any reference images, chosen preset, chosen optics.
- Output: the structured caption schema above, then rendered into the target model's preferred prompt style (each vendor adapter has a style card: Seedance likes shot-list style, Veo likes prose, Kling likes explicit camera verbs).
- Include a "faithfulness" rule: never add subjects or actions the user did not imply; only add lighting, lens and composition detail.
- Cache by hash of inputs.

**4.4 Post-processing chain (all off-the-shelf)**

| Stage | Component |
|---|---|
| Spatial upscale to 4K | Real-ESRGAN video variant, or a diffusion upscaler (SeedVR2 / Wan-based tile upscaler) for the premium tier |
| Temporal deflicker | All-in-one deflicker (Lei et al. 2023) or a learned temporal filter over optical-flow-aligned frames |
| Skin enhancement | Face-region detect (RetinaFace) then GPEN/CodeFormer at low fidelity weight (0.3 to 0.5) blended with a soft mask; never full-strength or it plasticizes |
| Relighting | See section 9 |
| Color pipeline | Optional LUT from Soul HEX palette |
| Audio | Route to Seed Audio or an in-house TTS/foley model; mux with ffmpeg |

---

## 5. Subsystem: conveying visual intent beyond words

### What Higgsfield does (evidence)

Higgsfield's core insight is to replace free-form language with *selectable structured controls* wherever words fail:

| Control | What it does | Grade |
|---|---|---|
| Camera presets (50 to 100+) | Dolly zoom, 360 orbit, push to glass, head tracking, crash zoom, bullet time, robo arm, FPV, handheld tracking | A |
| Start / end frame | Keyframe conditioning for i2v | B |
| Moodboards | Learn a custom aesthetic from multiple reference images | B |
| Soul HEX | Transfer a reference image's palette/colour | B |
| Reference images / Reference Elements | Saved characters, products, styles usable across Soul, Cinema Studio, Seedance 2.0, Kling 3.0 | B |
| Cinema Studio optics | Virtual camera body, lens type, focal length chosen before generation | B |
| AI Director | Drafts shots from a brief | B |
| Canvas graphs and saved templates | Reusable parameterized pipelines | A |
| Model versioning abstraction | Family, not version | A |

### Replication spec

**5.1 Preset library.** Each preset is a data record, not a prompt string:
```
{id, name, thumbnail_video, category,
 camera_traj: [ {t, R(3x3), T(3), fov} ... ] normalized over N frames,
 lens: {focal_mm, distortion},
 motion_hints: {subject_motion: "freeze"|"slowmo"|"natural"},
 prompt_suffix: "...",            // for licensed models lacking camera conditioning
 supported_models: [...]}
```
For DoP (section 8) the trajectory is fed as Plücker conditioning. For licensed models without camera input, the same record falls back to `prompt_suffix` plus, where supported, start/end frames rendered from a quick 3D proxy.

**5.2 Moodboards.** Implement as an image-set embedding plus optional fast LoRA:
- Encode each board image with a CLIP/SigLIP encoder and an IP-Adapter-style projector; average or attention-pool the tokens; inject into Soul via decoupled cross-attention (IP-Adapter / IP-Adapter-Plus). This gives instant "style from N images".
- For premium boards, train a style LoRA (rank 16, 800 to 1500 steps, captioned with a trigger token) in the background and hot-swap it in.

**5.3 Soul HEX (palette transfer).** Extract a 5 to 8 colour palette from the reference (k-means in CIELAB, weighted by saliency). Two injection points: (a) a text macro in the rewritten prompt listing named colours; (b) a ColorAdapter: a small conditioning MLP taking the palette embedding, trained by fine-tuning Soul on images paired with their own palettes with 30% dropout. Post-hoc fallback: Reinhard colour transfer in LAB plus a histogram-match LUT.

**5.4 Optics conditioning (Cinema Studio).** Add three scalar conditions to the video/image DiT via adaLN modulation, the same path as timestep: `focal_mm` (log-scaled), `sensor_size`, `f_stop`. Training labels come from EXIF for stills and from the VLM caption's `camera.lens_mm` estimate for video (noisy but sufficient with dropout). Camera body choice maps to a film-stock/colour-science LUT plus grain profile, applied in post; it does not need to be a model condition.

**5.5 AI Director.** An LLM agent (use a current Claude model or Gemini) with tools: `list_presets`, `list_references`, `get_model_capabilities`, `draft_shot_list`, `render_prompt(model_style_card)`. Given a brief, it returns a shot list where each shot is a fully specified `GenerationRequest` referencing preset ids and reference element ids. The user edits the list in the UI; only then are credits spent.

**5.6 Canvas.** A DAG editor (React Flow) whose nodes are `GenerationRequest`s with typed ports (image, video, text, reference_element, audio). Serialize graphs as JSON templates with declared input slots so "duplicate, swap inputs, re-run" works. Real-time multiplayer via CRDT (Yjs) as in Figma. Execution engine topologically sorts, batches independent nodes, and streams results.

---

## 6. Subsystem: face swap, character swap and identity

### What Higgsfield does (evidence)

Three distinct mechanisms, not one:

1. **Soul ID (A):** a per-user trained identity. Upload 20 to 80 photos (varied angles and expressions, at least one full-body, no sunglasses or heavy shadows). Training takes 3 to 5 minutes. The identity is then a selectable "character" in Soul, saved as a Reference Element, and carried into video models via reference or keyframe images. Higgsfield explicitly compares it to Stable Diffusion LoRA ("Soul ID gives most of that consistency with none of the pipeline") and it is not exportable as a file. This is a lightweight per-identity fine-tune on the Soul base model.
2. **Reference-image anchoring (A, from Higgsfield's own blog):** a single reference "anchors to that specific image at that specific angle in that specific lighting" and drifts when the scene changes. This is zero-shot identity injection and Higgsfield presents it as the weaker option that Soul ID fixes.
3. **Face Swap and Character Swap "Recast" (B):** Higgsfield's engineer guide frames these as tips for "the WAN 2.2 engine", i.e. built on Alibaba's open Wan 2.2-Animate model. Face swap "tracks facial geometry, skin tone, and lighting across every frame", processes video frame-by-frame with the clip as base, analyzes source and target before merging, supports one face per operation (the face closest to camera), and takes 30 s to 2 min. Recast replaces the full persona (body, clothing, posture, gestures) driven by the original actor's motion, keeps the original camera choreography, and bundles voice cloning and dubbing. A third-party report says Character Swap shipped via a Kling partnership, so the product may route between Wan-Animate and Kling V2V depending on tier.

### Replication spec

**6.1 Soul ID (per-identity fine-tune)**

- Preprocess: RetinaFace detect, align, reject blur (Laplacian variance threshold), reject duplicates, reject occlusions; auto-caption each photo with the VLM using a fixed trigger token `<sks_person>` plus wardrobe/background description (so the model learns the face, not the clothes).
- Train a rank-32 LoRA on the Soul DiT's attention and FFN projections, plus a learned textual token for the identity, 600 to 1200 steps at batch 4, lr 1e-4, with prior-preservation regularization images (generated by base Soul from "a person" prompts). At 3 to 5 minutes wall-clock, this fits a single H100 with a cached text encoder and precomputed latents. Precompute latents at upload time so training begins immediately.
- Optionally also extract an ArcFace embedding and keep a pre-trained identity adapter (see 6.2) active at low weight during Soul ID generation. This is what makes identity survive extreme style prompts.
- Store the LoRA server-side keyed to the user; never expose the file (matches Higgsfield's non-exportability).
- Quality gate: after training, generate 8 test images and compute ArcFace cosine to the upload set; if the mean is below 0.55, retrain with 300 more steps or ask for more photos.

**6.2 Zero-shot reference anchoring (single image, image and video)**

- Image: IP-Adapter-FaceID-Plus or PuLID on the Soul base. ArcFace ID embedding plus CLIP face patch tokens via decoupled cross-attention. Train once, on 1 to 2M face images with the same-person pairing from a curated face dataset.
- Video: Stand-In architecture (CVPR 2026, open code on Wan 2.1/2.2). VAE-encode the reference face as a one-frame latent, patchify with the video patchifier, concatenate its tokens to the video token sequence in every DiT block. Add rank-128 LoRA on q/k/v applied only to the face tokens. Restricted self-attention: face tokens attend only to themselves; video tokens attend to both. RoPE for face tokens uses frame index 0 with height and width frequencies offset past the video extent. Only ~1% extra parameters (153M on Wan 14B). Train on ~1M identity-paired video clips (same person, different clip) for 10k to 20k steps.
- Carrying a Soul ID into licensed video models: generate a start frame with Soul + the Soul ID LoRA, then submit that frame plus 2 to 3 additional Soul-rendered views of the character as reference images to Seedance 2.0 / Kling 3.0 native reference slots. This matches Higgsfield's description that Soul ID works across those models without fine-tuning them.

**6.3 Face swap (video, face only)**

Pipeline, all per-frame with temporal tracking:
1. Face tracking: RetinaFace + ByteTrack; choose the track with the largest mean bounding box (the "closest to camera" rule).
2. Per-frame alignment to a 5-point template; extract 512×512 crops.
3. Identity: ArcFace/AntelopeV2 embedding of the source face.
4. Swap core, two tiers:
   - Fast tier: inswapper_128 (InsightFace) followed by GFPGAN/CodeFormer restoration, then Poisson blend with a dilated occlusion-aware mask (BiSeNet face parsing). 30 s for a 5 s clip.
   - Quality tier: identity-conditioned masked latent inpainting in the video DiT, as in Stand-In's face-swap mode: VAE-encode the source video, detect and dilate a face mask (kernel 10 in latent space), pick a denoising strength (0.5 to 0.7), and at every denoising step replace latents outside the mask with the noised original latents while the identity branch drives the masked region. This preserves lighting and camera exactly and handles large pose changes.
5. Colour and lighting match: per-frame LAB mean/std transfer from the target face region to the swapped face before blending.
6. Temporal consistency: warp the previous swapped frame with optical flow and blend 20% into the current before restoration.

**6.4 Character swap / Recast (full body)**

- Use Wan 2.2-Animate in "replace" mode: inputs are the driving video and a character reference image. The model extracts skeleton (DWPose) and facial motion from the driving video and re-renders the reference character performing it, with a relighting LoRA that adapts lighting to the target scene. Keep the original background and camera by masking the driven subject and compositing.
- Reference image guidance surfaced to users: textured background, full body visible, matching lighting. Higgsfield's own tip that pure-white backgrounds hurt results is a direct consequence of the model using background depth cues.
- Voice: speaker-embedding TTS (F5-TTS or CosyVoice) for cloning; translation via LLM; forced alignment with the original for timing; optional lip resync with LatentSync or MuseTalk.
- Runtime target: 1 to 2 minutes for a 5 to 10 s clip on one H100.

---

## 7. Subsystem: the reference anchor system and orchestration reasoning

### What "reference anchor" means at Higgsfield (evidence)

Higgsfield uses "anchor" in two related senses (grade A for the first, B for the second):

1. **Reference-image anchoring** as a technique: a reference image "anchors" identity, product or style for a single generation. Higgsfield's blog is explicit that this anchors to the image's angle and lighting and drifts under scene change.
2. **Reference Elements** as a product object: a Soul ID, a product shot, or a style can be saved once and re-used across Soul, Cinema Studio, Seedance 2.0, Kling 3.0 and Canvas nodes.

No first-party source describes a named "reasoning model" that orchestrates anchors. What is documented: an "AI Director" in Cinema Studio that drafts shots, Gemini used for "control over video generation", Canvas graphs routing outputs across models. The orchestration below is therefore a grade-C reconstruction that reproduces the observable behaviour.

### Replication spec

**7.1 Reference registry**

```
ReferenceElement {
  id, owner, kind: "character"|"product"|"style"|"environment",
  canonical_images[]: {url, view: "front"|"3/4"|"profile"|"full_body"|"detail"},
  identity: {soul_id_lora?: path, arcface_emb?: float[512], clip_emb: float[1024]},
  palette?: HEX[], style_lora?: path,
  text_descriptor: string  // VLM-written, stable across sessions
}
```
On creation, the system auto-generates the missing canonical views (for a character: Soul + Soul ID renders of front, three-quarter, profile, full-body under neutral lighting) so that later injections have an angle-appropriate reference. This is the fix for "anchors to that specific angle".

**7.2 Planner (the reasoning layer)**

An LLM agent with a tool interface. Plan format per shot:
```
Shot {
  intent: string,
  references: [{element_id, role: "subject"|"product"|"style"|"background", weight}],
  model_family, preset_id?, optics?, start_frame_source?, end_frame_source?,
  duration, aspect, prompt_structured: CaptionSchema
}
```
Planner responsibilities:
- Resolve each reference into the injection method the chosen model supports: Soul ID LoRA for Soul; native multi-reference slots for Seedance 2.0 / Kling 3.0 (pick the canonical view whose angle matches the requested shot); Stand-In conditioning for DoP; start-frame injection for models without reference inputs.
- Rewrite prompts using each reference's `text_descriptor` so text and image conditioning agree (disagreement is the main cause of drift).
- Choose the model family from capabilities and the user's stated priority (realism -> Seedance; long/multi-shot -> Kling; camera work -> DoP; text in frame -> GPT Image).
- After generation, run a **consistency check**: ArcFace cosine between the output's detected face and the character's embedding; CLIP similarity for products and styles. Below threshold, automatically retry with higher reference weight or a different canonical view, up to 2 times. This closed loop is what makes the system feel like it "reasons" about anchors.

**7.3 Multi-shot continuity**

- Maintain a per-project "scene state": environment reference element, lighting descriptor, palette, last frame of each shot.
- For consecutive shots, pass the previous shot's last frame as the start frame (Kling/Seedance) or as a conditioning clip (DoP with CameraCtrl II-style clip-to-clip continuation, section 8).

---

## 8. Subsystem: Higgsfield DoP (Director of Photography)

### What Higgsfield says (grade A, verified)

- DoP I2V-01-preview (launched ~31 Mar 2025) is Higgsfield's **own image-to-video model**, exposed in the product as "Higgsfield Standard" and via third-party APIs (Segmind, WaveSpeed, ComfyUI Cloud). The three-vote check refuted an earlier claim that DoP was merely a preset layer rather than a model.
- Architecture: "a novel architecture that blends diffusion models with reinforcement learning", explicitly likened to DeepSeek-style RL post-training. "Rather than simply denoising frames, it's trained to understand and direct motion, lighting, lensing, and spatial composition."
- Exposed via 50 to 100+ named presets applied to a single input image; tiers Lite / Turbo / Preview; start/end frame support.
- Inference runs on AMD MI300X (TensorWave) and Nebius.
- Cinema Studio later applies camera-control logic across Seedance 2.0, Veo 3.1 and Kling 3.0 too (grade B), which is consistent with prompt-side and keyframe-side fallbacks for models Higgsfield does not control.

### Published methods this maps onto

| Method | Contribution | Openness |
|---|---|---|
| CameraCtrl (2024) | Per-pixel Plücker ray embeddings from extrinsics/intrinsics, multi-scale camera encoder injected into temporal attention of a frozen video diffusion model; trained on RealEstate10K; two-stage (domain LoRA then camera module); presets are just stored pose files | Code and weights |
| MotionCtrl (SIGGRAPH 2024) | Decoupled Camera Motion Control Module (RT matrices appended to temporal self-attention via FC) and Object Motion Control Module (point trajectories); plug-in on LVDM/SVD/AnimateDiff | Code and weights |
| CameraCtrl II (ICCV 2025, ByteDance Seed) | DiT-era lightweight camera injection that preserves dynamics; purpose-built high-dynamics dataset with camera annotations; autoregressive clip-to-clip exploration; ~5x more motion and ~2x lower pose error than CameraCtrl v1 | Paper only |
| ReCamMaster (ICCV 2025 oral, Kuaishou) | Source-video tokens concatenated with target tokens along the frame dimension; MultiCamVideo dataset: 13.6K UE5 dynamic scenes × 10 synchronized cameras = 136K videos at 1280², 81 frames, with Pan/Tilt, Translation, Arc, Random, Static trajectories | Code, Wan 2.1 weights, dataset |

### Replication spec

**8.1 Backbone.** Wan 2.2 14B I2V (open) as the diffusion backbone, or the human-centric continued-pretrain from section 4.2. Image conditioning is the native i2v path (first-frame latent concatenation).

**8.2 Camera conditioning (CameraCtrl II recipe).**
- Represent each preset as per-frame extrinsics `[R|t]` and intrinsics `K` at the model's latent frame rate.
- Compute per-pixel Plücker coordinates `(d, o × d)` for each latent frame, in coordinates relative to the previous frame (the Seaweed-APT2 modification that prevents unbounded growth on long orbits), scaled to roughly unit standard deviation.
- Patchify the 6-channel Plücker map with the same 3D patchifier as the video latents and add the result to the visual token embeddings through a zero-initialized (or small-random-initialized) projection. This is a few million parameters.
- Train with the DiT unfrozen at low learning rate (1e-5) and the camera projection at 1e-4, so dynamics are preserved (freezing the DiT as in CameraCtrl v1 caused the static-scene collapse that CameraCtrl II fixes).
- Also add MotionCtrl-style object trajectory control as a second optional channel (sparse point tracks rendered as Gaussian heatmaps) for presets like head tracking and push-to-glass where the subject must stay locked.

**8.3 Data.**
1. Real footage with SfM camera labels: the human-centric corpus from section 4.1 with VGGSfM/MegaSaM trajectories, filtered to clips where reprojection error is low. Keep only clips with substantial subject motion so the model learns camera and subject motion as independent factors.
2. Synthetic paired data: extend ReCamMaster's MultiCamVideo approach in Unreal Engine 5 with Metahuman actors and the specific preset trajectories (crash zoom, dolly zoom with focal change, 360 orbit, bullet time with frozen actors, robo arm arcs, FPV). Target 20K scenes × 10 cameras. This is the only practical way to get exact-trajectory ground truth for exotic moves.
3. Preset-specific curation: for bullet time, freeze the animation and sweep the camera; for dolly zoom, co-vary focal length and dolly distance so subject size stays constant.

**8.4 RL post-training (the part Higgsfield emphasizes).**
- Reward components, computed on sampled videos:
  - Camera accuracy: run VGGSfM on the output, align to the target trajectory, negative translation and rotation error (the CameraCtrl II benchmark metrics).
  - Dynamics preservation: RAFT optical-flow magnitude on foreground masks, rewarded within a target band (so the scene does not freeze).
  - Geometric consistency: VGGSfM success rate and reprojection error.
  - Aesthetic and realism: the section 4.2 reward model, plus human preference on cinematic quality (collect 20k pairs specifically on camera moves).
  - Identity preservation: ArcFace cosine between input image and output frames.
- Algorithm: Flow-GRPO (group-relative policy optimization for flow-matching models) or DanceGRPO, 8 samples per prompt-preset pair, KL penalty to the supervised checkpoint, 2k to 5k steps. Run at reduced resolution (480p) and verify transfer to 720p/1080p.

**8.5 Multi-clip continuation.** For long moves, condition on the previously generated clip's tokens (ReCamMaster's frame-dimension concatenation) and continue the trajectory; CameraCtrl II demonstrates this keeps scene consistency and even supports 3D reconstruction from the outputs.

**8.6 Serving.** Distill three tiers: Preview (full model, 50 steps), Turbo (8-step distilled via DMD2 or self-forcing), Lite (fewer frames, 480p). Use FP8 on MI300X/H100; TensorWave's MI300X 192GB memory is why a 14B DiT with long token sequences serves comfortably there.

**8.7 Fallback for licensed models.** For each preset also store a prompt suffix and, where the vendor exposes it, its own camera-control enum (Kling has camera controls; Seedance 2.0 accepts multi-shot and reference inputs). Render a preview trajectory as start and end frames using a monocular 3D proxy (depth from Depth Anything V2 + point cloud reprojection) when the vendor supports keyframes.

---

## 9. Subsystem: ML layers, relighting, generative fill

### What Higgsfield does (grade B)

- **Layers:** splits a flat image into background, subject and other elements; default 5 layers; 1K/1.5K/2K output; Standard vs Fast mode; text re-rendering; native 4K.
- **Generative Fill:** driven by the "Nano Banana Pro engine" (Google Gemini image model), i.e. licensed.
- **Relighting:** "depth-aware" with direction, intensity, softness and colour-temperature controls.
- Canvas and inpainting pages tie these together as an edit stack rather than a separate proprietary model.

### Replication spec

**9.1 Layer decomposition**

1. Instance and semantic parsing: SAM 2 with automatic mask generation, merged with Grounding DINO labels; rank instances by area and saliency; cap at N layers (default 5): background, primary subject, secondary subjects, foreground occluders, text.
2. Text layer: OCR (PaddleOCR) to detect text regions; a separate "text re-rendering" path re-typesets recognized text with a matching font via a text-to-image model with layout conditioning (AnyText / GlyphControl) so users can edit copy.
3. Amodal completion per layer: for every non-background layer, inpaint the occluded parts of the object (Pix2Gestalt-style amodal segmentation, then a diffusion inpainter conditioned on the object's visible region). Without this step, moving a layer reveals holes.
4. Background completion: remove all foreground masks and inpaint with LaMa (fast mode) or a diffusion inpainter (standard mode) so the background is a full plate.
5. Alpha matting per layer: ViTMatte or Matte Anything on a trimap derived from the SAM mask for hair and soft edges.
6. Export as ordered RGBA layers plus a depth map (Depth Anything V2) so the canvas can place layers in 2.5D.

Speed: fast mode uses SAM 2 + LaMa at 1K (~3 s); standard mode uses diffusion inpainting at 2K (~20 s).

**9.2 Depth-aware relighting**

- Estimate depth (Depth Anything V2) and normals (from depth, or Marigold/StableNormal).
- Foreground relighting: IC-Light (Zhang et al.), conditioned on a background or a light-direction map. Map UI controls to conditioning: direction -> a rendered gradient light map over the normal field; intensity -> scale of the map; softness -> Gaussian blur radius of the map; colour temperature -> RGB tint of the map.
- Shadow synthesis: project the subject alpha along the light direction using the depth map to cast a contact shadow on the background layer; blur by softness.
- Video relighting: run IC-Light per frame with the same light map, then temporal smoothing via optical-flow warp blending; or use a video relighting model (Light-A-Video style) for the premium tier.

**9.3 Generative fill and edit**

- Default path: call the licensed image editing model (Gemini image, "Nano Banana Pro") with mask + instruction. Higgsfield does this too.
- Self-hosted fallback: FLUX.1 Fill or Qwen-Image-Edit with the same interface.
- Compositing back: match layer exposure and white balance to the background (per-channel LAB statistics), harmonize with a harmonization net (Harmonizer) for seamless blends.

---

## 10. Data, training and cost plan

| Component | Base | Data | Compute (order of magnitude) |
|---|---|---|---|
| Soul image model | FLUX-class or SD3.5-class DiT, or own 8B DiT | 100M+ captioned images, heavy on fashion/portrait; VLM captions in the schema | 2k to 5k H100-days for continued pretrain + aesthetics RL |
| Soul ID | Soul + LoRA per user | user uploads | 1 H100 × 3 to 5 min per identity |
| Identity adapters | Stand-In on Wan; PuLID/IP-Adapter-FaceID on Soul | 1M identity-paired clips; 2M face images | 100 to 300 H100-days |
| Video base (realism) | Wan 2.2 14B | 10 to 50M human-centric clips, VLM-captioned, SfM-labelled | 5k to 20k H100-days |
| DoP camera module + RL | above | real SfM clips + 200K UE5 synthetic videos | 300 to 1k H100-days |
| Layers / relight | SAM 2, LaMa, IC-Light, Depth Anything V2 | mostly pre-trained; fine-tune inpainter on product/fashion | <50 H100-days |
| Captioner | Gemini API or Qwen2.5-VL 72B | | inference only |

The largest single cost is the VLM captioning of tens of millions of clips. Higgsfield's claim of 50% better caption matching using Gemini says they treated captioning as a first-class investment; budget for it.

---

## 11. Serving and infrastructure

- Training: Google Cloud (Vertex AI / A3 H100 or TPU v5p) as Higgsfield does; or any H100 cluster.
- Inference: separate pools per model class. DoP and Wan-based identity models on MI300X or H100 with FP8, torch.compile, and CFG-distilled checkpoints. Soul on L40S/H100 at ~2 s/image with 8-step distillation.
- Licensed models: vendor APIs behind the adapter layer with per-vendor concurrency limits and fallback across families when a vendor is down (users chose a family, so silent version fallback is acceptable; family fallback should be surfaced).
- Storage: all inputs, intermediates and outputs retained with lineage for Canvas re-runs.
- Safety: face-swap and Soul ID require consent attestation; C2PA provenance manifests on outputs; NSFW and public-figure classifiers on identity uploads.

---

## 12. Product surface to match

| Feature | Notes |
|---|---|
| Model picker by family with automatic latest version | section 3 |
| Preset browser with looping thumbnails | each preset a stored trajectory record |
| Soul ID: upload 20 to 80 photos, train in minutes, character tab | section 6.1 |
| Moodboards, Soul HEX, reference elements | section 5 |
| Cinema Studio: camera body, lens, focal length, AI Director shot list | section 5.4, 5.5 |
| Canvas: node graph, templates, multiplayer | section 5.6 |
| Layers, relight, generative fill | section 9 |
| Face swap, Recast with dubbing and voice clone | section 6.3, 6.4 |
| Post: 4K upscale, deflicker, skin, audio | section 4.4 |
| API with the same endpoints; credits per node | section 3 |

---

## 13. Confidence summary

| Claim | Grade |
|---|---|
| Higgsfield licenses Seedance/Kling/Veo/Sora/Wan/Hailuo and routes video to them; DoP layered on top | A (verified) |
| Soul is Higgsfield's own image model; Soul ID is a train-once identity from 20 to 80 photos in minutes | A (verified) |
| DoP is a proprietary i2v model combining diffusion with RL post-training, exposed via presets | A (verified; the "only a layer" reading was refuted) |
| Gemini used for captioning and control; in-house model scoped to people, faces, camera, lighting; trained on GCP | A (first-party case study) |
| Canvas is a multi-model node graph with templates and multiplayer | A (first-party page, multiple snippets) |
| Face swap / Recast built on Wan 2.2-Animate; closest-face targeting; one face per op | B (first-party engineer blog) |
| Character Swap shipped via Kling partnership | B (single third-party report) |
| Layers: 5-layer default, 1K to 2K, text re-render; Generative Fill on Nano Banana Pro; depth-aware relight | B (first-party product pages via snippets) |
| Post-processing: 4K upscale, deflicker, skin enhancement | B (third-party inventory) |
| Cinema Studio optics conditioning and AI Director | B (first-party blog) |
| Soul ID is a LoRA-style fine-tune rather than zero-shot embedding | C (strong inference from training time, photo count, non-exportability and Higgsfield's own LoRA comparison) |
| DoP camera conditioning uses Plücker embeddings and CameraCtrl II-style injection | C (inference; Higgsfield has published no architecture details) |
| An LLM planner resolves reference anchors and checks consistency | C (reconstruction of observed behaviour) |
| Funding, valuation and revenue figures | B (TechCrunch/Wikipedia snippets; page fetches blocked) |

---

## 14. Sources

First-party (Higgsfield):
- https://higgsfield.ai/creator-hub/help-center/ai-models/which-ai-model-should-i-use
- https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-dop
- https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-create-and-use-a-soul-id-character
- https://higgsfield.ai/blog/Introducing-Higgsfield-DoP-preview
- https://higgsfield.ai/blog/AMD-and-Higgsfield-DoP-TensorWave
- https://higgsfield.ai/blog/Why-Does-Your-AI-Characters-Face-Keep-Changing
- https://higgsfield.ai/blog/sould-id-best-character-consistency
- https://higgsfield.ai/blog/AI-Face-Character-Swap-in-Video-Photo-PRO-Guide
- https://higgsfield.ai/blog/cinema-studio-guide
- https://higgsfield.ai/blog/seedance-2-0-pricing-2026
- https://higgsfield.ai/canvas-intro
- https://higgsfield.ai/soul-intro
- https://higgsfield.ai/camera-controls
- https://higgsfield.ai/higgsfield-layers
- https://cloud.google.com/transform/3-lessons-for-gen-ai-startups-higgsfield-ai-infrastructure-talent-models

Third-party reporting and reviews:
- https://techcrunch.com/2026/08/17/higgsfield-raises-400m-series-b-quadrupling-its-valuation-in-8-months-to-5-4b/
- https://en.wikipedia.org/wiki/Higgsfield_AI
- https://www.cnbc.com/video/2026/08/17/higgsfield-ceo-alex-mashrabov-on-new-funding-round-ai-content-creation-battle-and-growth-outlook.html
- https://sacra.com/research/alex-mashrabov-higgsfield-ai-video-production/
- https://skybreakai.com/blog/higgsfield-models-explained-2026
- https://aireiter.com/blog/higgsfield-ai-reviews-pricing-vs-api
- https://pollo.ai/hub/higgsfield-ai-review
- https://www.therundown.ai/tools/higgsfield
- https://perplexityaimagazine.com/ai-news/higgsfield-ai-character-swap-photorealistic-video/
- https://apiframe.ai/guides/higgsfield-api-guide
- https://www.segmind.com/models/higgsfield-image2video

Research:
- CameraCtrl, arXiv 2404.02101, https://github.com/hehao13/CameraCtrl
- CameraCtrl II, arXiv 2503.10592, ICCV 2025
- MotionCtrl, arXiv 2312.03641, https://github.com/TencentARC/MotionCtrl
- ReCamMaster, arXiv 2503.11647, MultiCamVideo dataset
- Stand-In, arXiv 2508.07901, CVPR 2026
- Concat-ID arXiv 2503.14151; MagicMirror arXiv 2501.03931; ConsisID; EchoVideo
- Seaweed-APT2 (Autoregressive Adversarial Post-Training), Appendix G, for the relative-Plücker modification
- InsightFace blog, March 2026 face swapping papers, https://www.insightface.ai/blog/march-2026-face-swapping-papers
