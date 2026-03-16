---
title: "FLUX.2-klein-4B CoreML Conversion"
description: "Converting a 4B-parameter image generation model from PyTorch to on-device CoreML for iOS deployment"
---

**Prepared:** March 13, 2026

---

## What is FLUX.2-klein-4B?

FLUX.2-klein-4B is a 4-billion-parameter image generation model from [Black Forest Labs](https://blackforestlabs.ai/) (BFL), the team behind the original Stable Diffusion. Released January 2026 under an Apache 2.0 license, it's the first commercially-licensed model that can do all three things we need in a single unified architecture:

1. **Generate** an image from a text prompt
2. **Transform** an existing image guided by a prompt (style transfer, aging, etc.)
3. **Compose** multiple images into one, guided by a prompt (put person A into scene B)

The architecture is fundamentally different from earlier diffusion models like SDXL:

| | SDXL (2023) | FLUX.2-klein-4B (2026) |
|---|---|---|
| Core network | U-Net | MM-DiT transformer |
| Text encoder | Dual CLIP (two separate encoders) | Single Qwen3 (full language model, 2560-dim, 36 layers) |
| Denoising method | DDPM noise prediction | Flow matching (velocity prediction) |
| Image conditioning | Noise injection (img2img only) | In-context tokens (images as input alongside text) |
| Latent channels | 4 | 32 |
| Steps needed | 20-50 | 4 (distilled) |
| CFG required | Yes (two forward passes) | No (single pass) |

The flow-matching scheduler and in-context conditioning are what make compose mode possible natively — reference images become additional tokens that the transformer attends to, rather than being injected as noise.

## The Reference Pipeline

BFL provides a Python reference implementation via Hugging Face's `diffusers` library (`Flux2KleinPipeline`). To use it, you need:

- Python 3.13+
- PyTorch with GPU support
- `diffusers >= 0.37.0`, `transformers`, `accelerate`
- ~8 GB of model weights in BFloat16
- An NVIDIA GPU with 16+ GB VRAM (or Apple Silicon with MPS)

On my M3 Max (64 GB), the reference pipeline generates images in 17-22 seconds depending on mode. On a cloud GPU, it's faster. Either way, it's a server-side workflow — you download ~8 GB of model weights, install a Python stack, and run inference on a machine with serious compute.

This is fine for research and development. It's not fine for shipping to someone's iPhone.

## Why CoreML?

[Vorge](https://vorge.app) is an iOS app for casual, social image generation — think "intelligent Instagram filters." The app has two tiers:

- **Premium**: API-based generation (fast, high quality, costs money per image)
- **Free**: Fully on-device generation via CoreML (no server, no cost, works offline)

The free tier is the hard one. It means running this entire pipeline — text encoder, transformer, VAE — directly on the phone's Neural Engine, with no Python runtime, no PyTorch, no server dependency. Everything happens in Swift with Apple's CoreML framework.

No one has done this conversion for FLUX.2-klein-4B. The model is too new, and the architecture is too different from what existing CoreML conversion tools expect.

## The Three Modes: Reference vs. Our Pipeline

Each mode maps differently from BFL's Python implementation to our CoreML pipeline:

### Generate (txt2img)

**What it does:** Text prompt in, image out.

**BFL reference:** `Flux2KleinPipeline.__call__(prompt="raccoon astronaut on the moon")` — the scheduler creates pure noise latents, the transformer denoises them conditioned on text embeddings, and the VAE decodes to pixels.

**Our CoreML pipeline:** Same flow, but every component is a CoreML `.mlpackage` model. The Qwen3 text encoder runs with live tokenization in Swift (no Python tokenizer dependency). The transformer runs 6 denoising steps (we found +6% quality over BFL's default of 4). The VAE decodes at FP16 precision.

**Quality:** 8.35/10 composite score — essentially matching the API tier.

### Transform (img2img)

**What it does:** Source image + text prompt in, transformed image out. "Make this photo look like an 80s ski trip."

**BFL reference:** The source image is encoded through the VAE encoder to get latents, noise is added at a controlled strength, and the transformer denoises back toward an image that matches the prompt while preserving the source structure.

**Our CoreML pipeline:** Same flow with CoreML VAE encoder + decoder. We always use `denoise_strength=1.0` (unlike SDXL where 0.5-0.8 is typical) because Klein's architecture handles source preservation through in-context conditioning, not through noise-level control.

**Quality:** 5.97/10 — source preservation is the weak point (4.07/10). The model frequently replaces faces during style transforms, which is an architectural limitation of the 4B parameter model, not a conversion artifact.

### Compose (multi-image + prompt)

**What it does:** 2-3 source images + text prompt in, composed image out. "Place this person in this scene."

**BFL reference:** All reference images are encoded as tokens and concatenated with the text tokens. The transformer attends to everything jointly. This is the architectural innovation — composition is native, not bolted on.

**Our CoreML pipeline:** Same in-context conditioning approach. We added a 3-tier aspect ratio selection system (described below) since the output dimensions need to be chosen intelligently from the source images.

**Quality:** 4.66/10 — the hardest mode. Scene-blending works well (scene+scene: 5.34), but people composition struggles (people+people: 4.29). The model treats identity as a loose style cue rather than a pixel-level constraint.

## Steps to Get There

### 1. Component Conversion (4 models)

Each component was converted from PyTorch to CoreML individually:

| Component | Original Size | Quantized Size | Method |
|-----------|--------------|---------------|--------|
| Qwen3 Text Encoder | 5,941 MB | 2,229 MB | 6-bit palettization |
| MM-DiT Transformer | 14,785 MB | 2,773 MB | 6-bit palettization |
| VAE Decoder | 95 MB | 95 MB | FP16 (no quantization) |
| VAE Encoder | 66 MB | 66 MB | FP16 (no quantization) |
| **Total** | **20,887 MB** | **5,162 MB** | **4.0x compression** |

Key challenges solved:
- **FP16 overflow in LayerNorm**: Qwen3 outputs up to ±16,384. Squaring that for LayerNorm variance exceeds FP16 max (65,504), producing NaN. Fixed by running compute in FP32.
- **4-bit quantization too aggressive**: The text encoder at 4-bit had 0.20 correlation with the original (garbled output). 6-bit works at 0.957 correlation.
- **torch.export required**: `jit.trace` (the old conversion path) is broken with coremltools 9.0. Switched to `torch.export` with ATEN decompositions.

### 2. Pipeline Reimplementation

The flow-matching scheduler and multi-mode conditioning logic were reimplemented in Python first (to validate against PyTorch reference), then ported to Swift. SSIM similarity to PyTorch reference: 0.39-0.40 for txt2img (expected from bf16→fp16 precision loss), 0.71 for img2img, 0.79 for compose.

### 3. Aspect Ratio Support

Three AR buckets: 1:1 (1024×1024), 3:4 (768×1024), 4:3 (1024×768). This required multi-function CoreML models — a single `.mlpackage` containing 7 transformer variants and 3 each for VAE encoder/decoder, with weight deduplication keeping the total at 5.1 GB (only +72 MB over single-AR).

### 4. Swift Port

Full Swift CLI with:
- Live Qwen3 tokenization via `swift-transformers` (no Python runtime)
- Runtime function selection for AR-aware inference
- CoreML model loading with `.mlmodelc` pre-compilation
- Performance: ~41s generate, ~75s transform, ~128s compose on M3 Max
- Peak RAM: ~3.7 GB for generate/transform, ~4.5 GB for 2-ref compose (fits iPhone 15 Pro Max)

### 5. Parameter Optimization

60+ runs across systematic parameter sweeps:
- **6 steps** recommended over BFL's default 4 (+6% quality, 50% more time — worth it for our use case)
- **No systematic seed structure** — seed variance is per-node noise, not a tunable knob
- **denoise_strength=1.0 always** — lower values hurt Klein unlike SDXL
- **Steps floor**: Even 1 step produces usable output (CLIP 28.32) — viable for fast previews

### 6. AR Selection for Compose

When composing multiple images, what aspect ratio should the output be? We built a 3-tier additive system:

1. **Tier 1 — Vote**: Majority vote across source image dimensions (EXIF-corrected)
2. **Tier 2 — Vision**: Apple Vision framework saliency + face detection analysis
3. **Tier 3 — LLM**: Apple Intelligence on-device reasoning via FoundationModels

The tiers disagree 86% of the time. After 2,286 LLM calls across 254 nodes × 3 modes × 3 runs, we found that `faces-only` mode (dropping saliency data, keeping only face count) gives the best results: 84.8% consistency, 52% agreement with Tier 1. The LLM has a systematic portrait bias (84%) that saliency data amplifies — removing saliency removes the noise.

Each tier is optional with graceful fallback for older devices.

## Safety & Quality Systems

### Scorer Engineering

We needed automated quality evaluation to benchmark at scale. The journey:

1. **GPT-4o**: Clustered all scores at 7-9, couldn't distinguish good outputs from broken ones. Identity replacement scored 7.3 when it should score 3.
2. **Three prompt iterations** (strict caps → distribution targets → balanced): Improved artifact detection but hit a structural ceiling on visual comparison.
3. **Claude Opus API**: Successfully detected merge artifacts (2.8 vs GPT-4o's 7.7) but had a "sycophancy problem" — described clearly broken outputs as high quality. Discrimination score: 0.12 (nearly zero).
4. **GPT-5.4 with v4 chain-of-thought prompts**: Discrimination score 3.53 (good outputs 7.55, bad outputs 4.02). Consistent (σ < 0.3), cheap (~$1.30 for 65 nodes), zero parse errors.

GPT-5.4 v4 CoT is our production scorer.

### AR Selection (3-tier)

Described above — uses on-device Apple Intelligence to choose output dimensions intelligently for compose mode, with fallback through Vision framework and simple voting for older devices.

### Quality vs. Mode

The scoring revealed a clear quality hierarchy that maps to product decisions:

| Mode | Score | Implication |
|------|-------|-------------|
| Generate | 8.35 | Ship confidently — matches API quality |
| Transform | 5.97 | Ship with caveats — identity preservation is weak |
| Compose (scene+scene) | 5.34 | Works well — lean into environment blending |
| Compose (people) | 4.18-4.29 | Risky — consider UI guidance away from multi-person composition |

### No Explicit NSFW Filter (Yet)

The pipeline does not include a safety classifier. BFL's model has some implicit safety training, but there's no hard filter. This is a remaining item for production.

## Where We Are

### 18 Phases Complete

| Phase | What | Key Result |
|-------|------|------------|
| 0 | Discovery & setup | Architecture mapped, all assumptions corrected |
| 1-4 | Component conversion | All 4 models → CoreML, individually validated |
| 5 | Python CoreML pipeline | All 3 modes working, SSIM 0.39-0.79 vs PyTorch |
| 6 | Benchmark v1 (txt2img) | 83% of API ceiling, 14 nodes |
| 7-10 | Quantization + Swift port | 5.2 GB total, live tokenization, no Python runtime |
| 11 | Benchmark v2 (all modes) | 89.5% of API ceiling, 14 real Vorge nodes |
| 12-13 | Parameter sweeps | 6 steps, no seed structure, no quality cliff |
| 14 | Aspect ratio support | 3 AR buckets, multi-function models, no quality regression |
| 15 | AR orientation fix | Dimension swap + EXIF handling fixed |
| 16 | Compose AR selection | 3-tier system (Vote + Vision + LLM), 82 nodes tested |
| 17 | LLM prompt experiment | 2,286 calls, faces-only mode wins |
| 18 | Full pipeline benchmark | 65 nodes scored by GPT-5.4: 5.16 overall composite |
| 18b | Scorer prompt engineering | GPT-4o ceiling identified, Claude prototype tested |
| 18c | Scorer model comparison | GPT-5.4 v4 CoT beats Claude Opus API |
| 18d | GPT-5.4 full rescore | Definitive 65-node benchmark with failure mode analysis |

All acceptance criteria from the original task are met.

### Remaining Work

1. **Neural Engine benchmark** — all testing so far uses `cpuAndGPU` compute units. Haven't tested `cpuAndNE` (Neural Engine), which is the actual target for iPhone deployment and could be significantly faster.

2. **8 GB device gating** — 3-ref compose is marginal at ~5 GB peak RAM. Need to test on real iPhone 15 Pro Max and potentially gate 3-ref compose on 8 GB devices.

3. **Source preservation improvements** — the model's Achilles heel (4.07-4.15 scores). This is likely an architectural limitation of 4B parameters, but pipeline-level tuning (adapter strength, two-pass generation) may help.

4. **NSFW safety classifier** — no hard content filter exists yet.

5. **ODR packaging** — models need to be split into ≤512 MB asset packs for Apple's On-Demand Resources delivery system.

6. **Production Swift integration** — the Swift CLI validates the pipeline works; it needs to be integrated into the Vorge iOS app as a framework.

### 48 Technical Lessons Documented

The full process document captures 48 lessons learned across all phases — from `torch.export` migration patterns to multi-function model weight deduplication to the discovery that high SSIM doesn't correlate with high quality (a node with SSIM 0.80 scored only 5.1/10 because it had high structural similarity but poor task completion).

### Six Identified Failure Modes

The GPT-5.4 benchmark identified six distinct failure patterns in compose/transform mode:

1. **Collage/split-screen** — model tiles sources side-by-side instead of integrating them
2. **Identity replacement** — generates plausible but wrong people (affects ~80% of transform nodes with faces)
3. **Subject fusion** — merges two subjects into one grotesque figure
4. **Source dropping** — picks one source image and ignores the others entirely
5. **Subject hallucination** — invents extra people or duplicates subjects
6. **Species/type change** — converts cats to humans during style transfer

These are documented with specific examples, root causes, and tuning priorities. Generate mode avoids all of them. The quality cliff from generate (8.35) to compose (4.66) is almost entirely about whether source identity must be preserved — when it doesn't (scene+scene, objects, stylized characters), composition works well.

---

*18 phases, 65 benchmark nodes, 2,286 LLM calls, 5.2 GB of quantized models, zero Python runtime dependencies. From a server-side research pipeline to something that fits in your pocket.*
