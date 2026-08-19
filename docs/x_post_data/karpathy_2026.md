---
title: "@karpathy 推文存档"
date: 2026-08-19
author: "@karpathy"
tags: ["20260803", "20260802", "20260722", "20260709", "20260703", "20260630", "20260624", "20260613", "20260610", "20260603", "20260531", "20260519", "20260512", "20260501", "20260428", "20260423", "20260410", "20260405", "20260403", "20260331", "20260328", "20260327", "20260326", "20260325", "20260321"]
---

# @karpathy

> 📊 推文存档 - 共 32 条推文

---

## 📊 数据概览

- **[20260803](./tags/20260803.html)**: 1 条
- **[20260802](./tags/20260802.html)**: 1 条
- **[20260722](./tags/20260722.html)**: 1 条
- **[20260709](./tags/20260709.html)**: 1 条
- **[20260703](./tags/20260703.html)**: 1 条
- **[20260630](./tags/20260630.html)**: 1 条
- **[20260624](./tags/20260624.html)**: 2 条

<details>
<summary>📋 查看更多 (18 个日期)</summary>

- **[20260613](./tags/20260613.html)**: 1 条
- **[20260610](./tags/20260610.html)**: 1 条
- **[20260603](./tags/20260603.html)**: 1 条
- **[20260531](./tags/20260531.html)**: 1 条
- **[20260519](./tags/20260519.html)**: 1 条
- **[20260512](./tags/20260512.html)**: 1 条
- **[20260501](./tags/20260501.html)**: 2 条
- **[20260428](./tags/20260428.html)**: 1 条
- **[20260423](./tags/20260423.html)**: 1 条
- **[20260410](./tags/20260410.html)**: 2 条
- **[20260405](./tags/20260405.html)**: 4 条
- **[20260403](./tags/20260403.html)**: 1 条
- **[20260331](./tags/20260331.html)**: 1 条
- **[20260328](./tags/20260328.html)**: 1 条
- **[20260327](./tags/20260327.html)**: 1 条
- **[20260326](./tags/20260326.html)**: 2 条
- **[20260325](./tags/20260325.html)**: 1 条
- **[20260321](./tags/20260321.html)**: 1 条

</details>

---

## 2026-08-03 00:10:51  {#_0803-001051}

🏷️ **[20260803](./tags/20260803.html)** 今日关注

R to @karpathy: More on the pelican on the bicycle test from @simonw: https://simonwillison.net/2025/Jun/6/six-months-in-llms/ I uploaded the source here so it's playable in the browser, forkable etc. https://karpathy.ai/lotr-movie/ Look out for GTA Hobbiton dropping before GTA VI :)

[📖 原文](https://nitter.net/karpathy/status/2083948654377996480#m)

[🔗 #0803-001051](#_0803-001051)

---

## 2026-08-02 11:00:09  {#_0802-110009}

🏷️ **[20260802](./tags/20260802.html)** 今日关注

We're starting to leave the territory where you'd test an LLM by e.g. "create an svg of pelican on a bicycle". As one idea to generalize it, I was interested what Opus 5 would do if I gave it the first paragraph of the Lord of the Rings, a 1M token budget (~$10) and asked for three js render of it. Opus went off for ~2 hours and wrote 5500 lines of code that (procedurally) rendered the story. It's kind of janky but fun. But it's a bit mindboggling that the LLM has to place and orchestrate various polygon assets in (x,y,z) coordinates and write code that animates it all, and that it even does anything at all. I also like this kind of examples because no one in their right mind would ever spend the time to write something this custom but LLMs have all the stamina and patience in the world, so it's an example where we go from "no one would ever do this" to "sure, why not, it's ~free". There might be a lot more. But I'm excited about creating hyper custom worlds that you can imagine dropping players into, e.g. here to participate in the LoTR story as a spectator NPC, or one of the characters, or etc. Something like an ephemeral GTA of X on demand. Last thought is that the domain of worlds/games exposes a weakness in LLMs: they can't easily audit their work because they aren't able to efficiently and natively perceive videos or play games within them. Here, Opus 5 had to very slowly and painstakingly take screenshots at different points, and it messed up a few times and created a bunch of jank. An example of raw capability (multimodal, gameplay) that I think is still quite lacking.

[📖 原文](https://nitter.net/karpathy/status/2083749667410727319#m)

[🔗 #0802-110009](#_0802-110009)

---

## 2026-07-22 00:53:55  {#_0722-005355}

🏷️ **[20260722](./tags/20260722.html)** 今日关注

One pattern I find useful for working with LLMs is a nice long ramble session. Sometimes the LLM needs more bits to understand what you're trying to achieve, but you're too lazy to type them. In these cases I like to lean back, switch to /voice and just ramble for like 10 minutes, total mess, anything goes, full stream of consciousness. Sometimes I declare it up top, something like "switching to speech recognition sorry for any typos...". Sometimes I turn it into a small interview of a few turns. But I find that the LLMs are somehow very good at reconstructing long incoherent rambles and often their echo of your own tangle of thoughts comes out quite a bit cleaner than what you started with. The result is that you improve the mind meld and have to correct things less from that point on.

[📖 原文](https://nitter.net/karpathy/status/2079610838143623371#m)

[🔗 #0722-005355](#_0722-005355)

---

## 2026-07-09 05:47:29  {#_0709-054729}

🏷️ **[20260709](./tags/20260709.html)** 今日关注

RT by @karpathy: Rewriting Bun in Rust https://bun.com/blog/bun-in-rust

[📖 原文](https://nitter.net/jarredsumner/status/2074973674332123157#m)

[🔗 #0709-054729](#_0709-054729)

---

## 2026-07-03 22:12:03  {#_0703-221203}

🏷️ **[20260703](./tags/20260703.html)** 本周精选

RT by @karpathy: I spent a LOT of time through the hardest 3D prompts at Fable, it is a 45 min video, but I have 60+ very cool demos for you. Also prompts in the next post. https://www.youtube.com/watch?v=rTc2_-1KuRE

[📖 原文](https://nitter.net/petergostev/status/2073047118801993910#m)

[🔗 #0703-221203](#_0703-221203)

---

## 2026-06-30 23:00:09  {#_0630-230009}

🏷️ **[20260630](./tags/20260630.html)** 今日关注

RT by @karpathy: We're coming out of stealth. We've built our first racks after a successful A0 tapeout, $1B+ in customer contracts, and $800m raised. Early customer tests show us achieving SOTA throughput, latency, and power efficiency on inference workloads. Our first racks ship this summer.

![图片 1](https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAIEqmpEJKbNou5fz4l6tTquMXVi_yuHAAKAEmsbitEhVr3tToEnkFRmAQADAgADeQADPAQ.jpg)

[📖 原文](https://nitter.net/Etched/status/2071972062202343590#m)

[🔗 #0630-230009](#_0630-230009)

---

## 2026-06-24 06:26:31  {#_0624-062631}

🏷️ **[20260624](./tags/20260624.html)** 今日关注

This is a new paradigm for interacting with Claude that is significantly more "inline" with all the other human activity org-wide. Once you do all of the under the hood engineering work to make this "just work" (e.g. across tools, integrations, compute environments, memory, security, etc.), Claude basically joins the team in a seamless way - you can talk to it as you would talk to a person and it can help with a very large variety of workloads. Imo this is the 3rd major redesign of LLM UIUX. The first paradigm was that the LLM is a website you go to, the second was that it is an app you download to your computer. This third one is that it is a self-contained, persistent, asynchronous entity with org-wide tools and context, working alongside teams of humans. It really takes a while to wrap your head around it, but it works and it is awesome.

![图片 1](https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAIDsWo7Dy_gahyDTKT05aYDyCjKRODBAAKOD2sbMUvYVdHATQABKcriMQEAAwIAA3kAAzwE.jpg)

[📖 原文](https://nitter.net/karpathy/status/2069547676849557725#m)

[🔗 #0624-062631](#_0624-062631)

---

## 2026-06-24 01:01:29  {#_0624-010129}

🏷️ **[20260624](./tags/20260624.html)** 今日关注

RT by @karpathy: Introducing Engram: Scaling compute on your context

![图片 1](https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAIDsmo7LEDCulh03wxh4IYsOQ898uSKAAKoD2sbMUvYVWZReJTV3v7zAQADAgADeQADPAQ.jpg)

[📖 原文](https://nitter.net/EngramLab/status/2069465879696576844#m)

[🔗 #0624-010129](#_0624-010129)

---

## 2026-06-13 01:45:54  {#_0613-014554}

🏷️ **[20260613](./tags/20260613.html)** 今日关注

In awe of SpaceX and its story - past, present and the future. You can think about it in 10+ different ways and continue re-blowing your mind in circles. Huge congrats to the team! 🚀

[📖 原文](https://nitter.net/karpathy/status/2065490793092337691#m)

[🔗 #0613-014554](#_0613-014554)

---

## 2026-06-10 02:10:00  {#_0610-021000}

🏷️ **[20260610](./tags/20260610.html)** 本周精选

This is a super exciting release - Claude Fable 5 is the same underlying model as Mythos but with added safeguards. The benchmarks are great and it's SOTA on everything by a margin but I'll add that *qualitatively* also, this is a major-version-bump-deserving step change forward (imo of the same order as Claude 4.5 was in November), peaking especially for long problem-solving sessions on very difficult problems. You can give it a lot more ambitious tasks than what you're used to, the model "gets it" and it will just go, and it's never felt this tempting to stop looking at the code at all (but don't do this in prod!). The model still has quirks that people will run into and the safeguards are configured to be a little too trigger happy for launch, which can hopefully be tuned over time.

I feel a lot of things changing as working software increasingly comes out on a tap. The Jevon's paradox kicks in and I feel my own demand for software growing substantially. You can ask for anything - explainers, visualizers, dashboards, bespoke single-use apps (e.g. a full wandb that is hyper-specific just for your project), you can 10X your test suite, auto-optimize code, run giant research projects with custom HTML for the results, anything! "Free your mind" (Matrix ref). Really looking forward to all the things people build!

![图片 1](https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAICImoqEV7iGonO2qrRecB60F8ckf8VAAIMFGsb5gdQVQ_8WUfh8ZCUAQADAgADeQADOwQ.png)

[📖 原文](https://nitter.net/karpathy/status/2064409694761054332#m)

[🔗 #0610-021000](#_0610-021000)

---

## 2026-06-03 04:26:32  {#_0603-042632}

🏷️ **[20260603](./tags/20260603.html)** 

RT by @karpathy: x.com/i/article/206185053570…

[📖 原文](https://nitter.net/trq212/status/2061907337154367865#m)

[🔗 #0603-042632](#_0603-042632)

---

## 2026-05-31 23:38:25  {#_0531-233825}

🏷️ **[20260531](./tags/20260531.html)** 

RT by @karpathy: This has quietly been a miracle month in medicine. 

In the last 5 weeks we’ve got news on:  

- retatrutide, the triple agonist GLP-1 from Lilly, basically melting fat and body-wide inflammation at record levels 
- RevMed’s new pancreatic cancer drug showing unprecedented abilities to extend life 
- small trial of a one-and-done PCSK9 gene editing therapy for slashing LDL cholesterol 
- Mayo’s AI-assisted radiology showing vastly improved cancer detection 
- this new therapy for metastatic solid tumors

This stuff is at varying levels of evidence. Retatrutide is ~100% on its way, other stuff needs more clinical trial data. But put it together and we’re maybe on the verge of majorly reducing the mortality of heart disease and cancer, the two leading causes of death in America.

![图片 1](https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAIBLmofWX_Gf2DMunJJj2_YRx6Ph_zDAAI-EWsbtcX5VJwZdRltE8TFAQADAgADeAADOwQ.png)

[📖 原文](https://nitter.net/DKThomp/status/2061110056293106118#m)

[🔗 #0531-233825](#_0531-233825)

---

## 2026-05-19 23:05:42  {#_0519-230542}

🏷️ **[20260519](./tags/20260519.html)** 

Personal update: I've joined Anthropic. I think the next few years at the frontier of LLMs will be especially formative. I am very excited to join the team here and get back to R&D. I remain deeply passionate about education and plan to resume my work on it in time.

[📖 原文](https://nitter.net/karpathy/status/2056753169888334312#m)

[🔗 #0519-230542](#_0519-230542)

---

## 2026-05-12 00:20:21  {#_0512-002021}

🏷️ **[20260512](./tags/20260512.html)** 

This works really well btw, at the end of your query ask your LLM to "structure your response as HTML", then view the generated file in your browser. I've also had some success asking the LLM to present its output as slideshows, etc.

More generally, imo audio is the human-preferred input to AIs but vision (images/animations/video) is the preferred output from them. Around a ~third of our brains are a massively parallel processor dedicated to vision, it is the 10-lane superhighway of information into brain. As AI improves, I think we'll see a progression that takes advantage:

1) raw text (hard/effortful to read)
2) markdown (bold, italic, headings, tables, a bit easier on the eyes) &lt;-- current default
3) HTML (still procedural with underlying code, but a lot more flexibility on the graphics, layout, even interactivity) &lt;-- early but forming new good default
...4,5,6,...
n) interactive neural videos/simulations

Imo the extrapolation (though the technology doesn't exist just yet) ends in some kind of interactive videos generated directly by a diffusion neural net. Many open questions as to how exact/procedural "Software 1.0" artifacts (e.g. interactive simulations) may be woven together with neural artifacts (diffusion grids), but generally something in the direction of the recently viral https://x.com/zan2434/status/2046982383430496444

There are also improvements necessary and pending at the input. Audio nor text nor video alone are not enough, e.g. I feel a need to point/gesture to things on the screen, similar to all the things you would do with a person physically next to you and your computer screen.

TLDR The input/output mind meld between humans and AIs is ongoing and there is a lot of work to do and significant progress to be made, way before jumping all the way into neuralink-esque BCIs and all that. For what's worth exploring at the current stage, hot tip try ask for HTML.

[📖 原文](https://nitter.net/karpathy/status/2053872850101285137#m)

[🔗 #0512-002021](#_0512-002021)

---

## 2026-05-01 01:43:06  {#_0501-014306}

🏷️ **[20260501](./tags/20260501.html)** 

This is the the quote I've been citing a lot recently.

[📖 原文](https://nitter.net/karpathy/status/2049907410303865030#m)

[🔗 #0501-014306](#_0501-014306)

---

## 2026-05-01 01:28:50  {#_0501-012850}

🏷️ **[20260501](./tags/20260501.html)** 

Fireside chat at Sequoia Ascent 2026 from a ~week ago. Some highlights:

The first theme I tried to push on is that LLMs are about a lot more than just speeding up what existed before (e.g. coding). Three examples of new horizons:

1. menugen: an app that can be fully engulfed by LLMs, with no classical code needed: input an image, output an image and an LLM can natively do the thing.
2. install .md skills instead of install .sh scripts. Why create a complex Software 1.0 bash script for e.g. installing a piece of software if you can write the installation out in words and say "just show this to your LLM".  The LLM is an advanced interpreter of English and can intelligently target installation to your setup, debug everything inline, etc.
3. LLM knowledge bases as an example of something that was *impossible* with classical code because it's computation over unstructured data (knowledge) from arbitrary sources and in arbitrary formats, including simply text articles etc.

I pushed on these because in every new paradigm change, the obvious things are always in the realm of speeding up or somehow improving what existed, but here we have examples of functionality that either suddenly perhaps shouldn't even exist (1,2), or was fundamentally not possible before (3).

The second (ongoing) theme is trying to explain the pattern of jaggedness in LLMs. How it can be true that a single artifact will simultaneously 1) coherently refactor a 100,000-line code base *and* 2) tell you to walk to the car wash to wash your car. I previously wrote about the source of this as having to do with verifiability of a domain, here I expand on this as having to also do with economics because revenue/TAM dictates what the frontier labs choose to package into training data distributions during RL. You're either in the data distribution (on the rails of the RL circuits) and flying or you're off-roading in the jungle with a machete, in relative terms. Still not 100% satisfied with this, but it's an ongoing struggle to build an accurate model of LLM capabilities if you wish to practically take advantage of their power while avoiding their pitfalls, which brings me to...

Last theme is the agent-native economy. The decomposition of products and services into sensors, actuators and logic (split up across all of 1.0/2.0/3.0 computing paradigms), how we can make information maximally legible to LLMs, some words on the quickly emerging agentic engineering and its skill set, related hiring practices, etc., possibly even hints/dreams of fully neural computing handling the vast majority of computation with some help from (classical) CPU coprocessors.

[📖 原文](https://nitter.net/karpathy/status/2049903821095354523#m)

[🔗 #0501-012850](#_0501-012850)

---

## 2026-04-28 05:34:34  {#_0428-053434}

🏷️ **[20260428](./tags/20260428.html)** 

RT by @karpathy: New work with @AlecRad and @DavidDuvenaud:

Have you ever dreamed of talking to someone from the past? Introducing talkie, a 13B model trained only on pre-1931 text. 

Vintage models should help us to understand how LMs generalize (e.g., can we teach talkie to code?). Thread:

[📖 原文](https://nitter.net/status_effects/status/2048878495539843211#m)

[🔗 #0428-053434](#_0428-053434)

---

## 2026-04-23 00:00:05  {#_0423-000005}

🏷️ **[20260423](./tags/20260423.html)** 

RT by @karpathy: Imagine every pixel on your screen, streamed live directly from a model. No HTML, no layout engine, no code. Just exactly what you want to see.

@eddiejiao_obj, @drewocarr and I built a prototype to see how this could actually work, and set out to make it real. We're calling it Flipbook. (1/5)

[📖 原文](https://nitter.net/zan2434/status/2046982383430496444#m)

[🔗 #0423-000005](#_0423-000005)

---

## 2026-04-10 04:38:48  {#_0410-043848}

🏷️ **[20260410](./tags/20260410.html)** 

R to @karpathy: Someone recently suggested to me that the reason OpenClaw moment was so big is because it's the first time a large group of non-technical people (who otherwise only knew AI as synonymous with ChatGPT as a website) experienced the latest agentic models.

[📖 原文](https://nitter.net/karpathy/status/2042341482531864741#m)

[🔗 #0410-043848](#_0410-043848)

---

## 2026-04-10 04:10:52  {#_0410-041052}

🏷️ **[20260410](./tags/20260410.html)** 

Judging by my tl there is a growing gap in understanding of AI capability.

The first issue I think is around recency and tier of use. I think a lot of people tried the free tier of ChatGPT somewhere  last year and allowed it to inform their views on AI a little too much. This is a group of reactions laughing at various quirks of the models, hallucinations, etc. Yes I also saw the viral videos of OpenAI's Advanced Voice mode fumbling simple queries like "should I drive or walk to the carwash". The thing is that these free and old/deprecated models don't reflect the capability in the latest round of state of the art agentic models of this year, especially OpenAI Codex and Claude Code.

But that brings me to the second issue. Even if people paid $200/month to use the state of the art models, a lot of the capabilities are relatively "peaky" in highly technical areas. Typical queries around search, writing, advice, etc. are *not* the domain that has made the most noticeable and dramatic strides in capability. Partly,  this is due to the technical details of reinforcement learning and its use of verifiable rewards. But partly, it's also because these use cases are not sufficiently prioritized by the companies in their hillclimbing because they don't lead to as much $$$ value. The goldmines are elsewhere, and the focus comes along.

So that brings me to the second group of people, who *both* 1) pay for and use the state of the art frontier agentic models (OpenAI Codex / Claude Code) and 2) do so professionally in technical domains like programming, math and research. This group of people is subject to the highest amount of "AI Psychosis" because the recent improvements in these domains as of this year have been nothing short of staggering. When you hand a computer terminal to one of these models, you can now watch them melt programming problems that you'd normally expect to take days/weeks of work. It's this second group of people that assigns a much greater gravity to the capabilities, their slope, and various cyber-related repercussions.

TLDR the people in these two groups are speaking past each other. It really is simultaneously the case that OpenAI's free and I think slightly orphaned (?) "Advanced Voice Mode" will fumble the dumbest questions in your Instagram's reels and *at the same time*, OpenAI's highest-tier and paid Codex model will go off for 1 hour to coherently restructure an entire code base, or find and exploit vulnerabilities in computer systems. This part really works and has made dramatic strides because 2 properties: 1) these domains offer explicit reward functions that are verifiable meaning they are easily amenable to reinforcement learning training (e.g. unit tests passed yes or no, in contrast to writing, which is much harder to explicitly judge),  but also 2) they are a lot more valuable in b2b settings, meaning that the biggest fraction of the team is focused on improving them. So here we are.

[📖 原文](https://nitter.net/karpathy/status/2042334451611693415#m)

[🔗 #0410-041052](#_0410-041052)

---

## 2026-04-05 22:58:44  {#_0405-225844}

🏷️ **[20260405](./tags/20260405.html)** 

R to @karpathy: Surprised with how good the comments on github gists are. A lot more helpful, insightful, constructive, a lot less AI... Is it the user community? The markdown format? The (lack of) incentives?

Suddenly feeling like I should gist more.
@github consider competing with X (?)

[📖 原文](https://nitter.net/karpathy/status/2040806346556428585#m)

[🔗 #0405-225844](#_0405-225844)

---

## 2026-04-05 07:28:36  {#_0405-072836}

🏷️ **[20260405](./tags/20260405.html)** 

Farzapedia, personal wikipedia of Farza, good example following my Wiki LLM tweet.

I really like this approach to personalization in a number of ways, compared to "status quo" of an AI that allegedly gets better the more you use it or something:

1. Explicit. The memory artifact is explicit and navigable (the wiki), you can see exactly what the AI does and does not know and you can inspect and manage this artifact, even if you don't do the direct text writing (the LLM does). The knowledge of you is not implicit and unknown, it's explicit and viewable.
2. Yours. Your data is yours, on your local computer, it's not in some particular AI provider's system without the ability to extract it. You're in control of your information. 
3. File over app. The memory here is a simple collection of files in universal formats (images, markdown). This means the data is interoperable: you can use a very large collection of tools/CLIs or whatever you want over this information because it's just files. The agents can apply the entire Unix toolkit over them. They can natively read and understand them. Any kind of data can be imported into files as input, and any kind of interface can be used to view them as the output. E.g. you can use Obsidian to view them or vibe code something of your own. Search "File over app" for an article on this philosophy.
4. BYOAI. You can use whatever AI you want to "plug into" this information - Claude, Codex, OpenCode, whatever. You can even think about taking an open source AI and finetuning it on your wiki - in principle, this AI could "know" you in its weights, not just attend over your data.

So this approach to personalization puts *you* in full control. The data is yours. In Universal formats. Explicit and inspectable. Use whatever AI you want over it, keep the AI companies on their toes! :)

Certainly this is not the simplest way to get an AI to know you - it does require you to manage file directories and so on, but agents also make it quite simple and they can help you a lot. I imagine a number of products might come out to make this all easier, but imo "agent proficiency" is a CORE SKILL of the 21st century. These are extremely powerful tools - they speak English and they do all the computer stuff for you. Try this opportunity to play with one.

[📖 原文](https://nitter.net/karpathy/status/2040572272944324650#m)

[🔗 #0405-072836](#_0405-072836)

---

## 2026-04-05 05:57:57  {#_0405-055757}

🏷️ **[20260405](./tags/20260405.html)** 

Something I've been thinking about - I am bullish on people (empowered by AI) increasing the visibility, legibility and accountability of their governments.

Historically, it is the governments that act to make society legible (e.g. "Seeing like a state" is the common reference), but with AI, society can dramatically improve its ability to do this in reverse. Government accountability has not been constrained by access (the various branches of government publish an enormous amount of data), it has been constrained by intelligence - the ability to process a lot of raw data, combine it with domain expertise and derive insights. As an example, the 4000-page omnibus bill is "transparent" in principle and in a legal sense, but certainly not in a practical sense for most people. There's a lot more like it: laws, spending bills, federal budgets, freedom of information act responses, lobbying disclosures... Only a few highly trained professionals (investigative journalists) could historically process this information. This bottleneck might dissolve - not only are the professionals further empowered, but a lot more people can participate.

Some examples to be precise: Detailed accounting of spending and budgets, diff tracking of legislation, individual voting trends w.r.t. stated positions or speeches, lobbying and influence (e.g. graph of lobbyist -&gt; firm -&gt; client -&gt; legislator -&gt; committee -&gt; vote -&gt; regulation), procurement and contracting, regulatory capture warning lights, judicial and legal patterns, campaign finance... Local governments might be even more interesting because the governed population is smaller so there is less national coverage: city council meetings, decisions around zoning, policing, schools, utilities...

Certainly, the same tools can easily cut the other way and it's worth being very mindful of that, but I lean optimistic overall that added participation, transparency and accountability will improve democratic, free societies.

(the quoted tweet is half-ish related, but inspired me to post some recent thoughts)

![图片 1](https://telegraph-image-fork.pages.dev/file/AgACAgUAAxkDAAPMah16HcCfPuwxsWewucDFqPRTZOUAAhsSaxtIMulUK2twkkBToaIBAAMCAAN5AAM7BA.jpg)

[📖 原文](https://nitter.net/karpathy/status/2040549459193704852#m)

[🔗 #0405-055757](#_0405-055757)

---

## 2026-04-05 00:45:23  {#_0405-004523}

🏷️ **[20260405](./tags/20260405.html)** 

Wow, this tweet went very viral!

I wanted share a possibly slightly improved version of the tweet in an "idea file". The idea of the idea file is that in this era of LLM agents, there is less of a point/need of sharing the specific code/app, you just share the idea, then the other person's agent customizes & builds it for your specific needs.

So here's the idea in a gist format: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

You can give this to your agent and it can build you your own LLM wiki and guide you on how to use it etc. It's intentionally kept a little bit abstract/vague because there are so many directions to take this in. And ofc, people can adjust the idea or contribute their own in the Discussion which is cool.

[📖 原文](https://nitter.net/karpathy/status/2040470801506541998#m)

[🔗 #0405-004523](#_0405-004523)

---

## 2026-04-03 04:42:21  {#_0403-044221}

🏷️ **[20260403](./tags/20260403.html)** 

LLM Knowledge Bases

Something I'm finding very useful recently: using LLMs to build personal knowledge bases for various topics of research interest. In this way, a large fraction of my recent token throughput is going less into manipulating code, and more into manipulating knowledge (stored as markdown and images). The latest LLMs are quite good at it. So:

Data ingest:
I index source documents (articles, papers, repos, datasets, images, etc.) into a raw/ directory, then I use an LLM to incrementally "compile" a wiki, which is just a collection of .md files in a directory structure. The wiki includes summaries of all the data in raw/, backlinks, and then it categorizes data into concepts, writes articles for them, and links them all. To convert web articles into .md files I like to use the Obsidian Web Clipper extension, and then I also use a hotkey to download all the related images to local so that my LLM can easily reference them.

IDE:
I use Obsidian as the IDE "frontend" where I can view the raw data, the the compiled wiki, and the derived visualizations. Important to note that the LLM writes and maintains all of the data of the wiki, I rarely touch it directly. I've played with a few Obsidian plugins to render and view data in other ways (e.g. Marp for slides).

Q&A:
Where things get interesting is that once your wiki is big enough (e.g. mine on some recent research is ~100 articles and ~400K words), you can ask your LLM agent all kinds of complex questions against the wiki, and it will go off, research the answers, etc. I thought I had to reach for fancy RAG, but the LLM has been pretty good about auto-maintaining index files and brief summaries of all the documents and it reads all the important related data fairly easily at this ~small scale.

Output:
Instead of getting answers in text/terminal, I like to have it render markdown files for me, or slide shows (Marp format), or matplotlib images, all of which I then view again in Obsidian. You can imagine many other visual output formats depending on the query. Often, I end up "filing" the outputs back into the wiki to enhance it for further queries. So my own explorations and queries always "add up" in the knowledge base.

Linting:
I've run some LLM "health checks" over the wiki to e.g. find inconsistent data, impute missing data (with web searchers), find interesting connections for new article candidates, etc., to incrementally clean up the wiki and enhance its overall data integrity. The LLMs are quite good at suggesting further questions to ask and look into.

Extra tools:
I find myself developing additional tools to process the data, e.g. I vibe coded a small and naive search engine over the wiki, which I both use directly (in a web ui), but more often I want to hand it off to an LLM via CLI as a tool for larger queries. 

Further explorations:
As the repo grows, the natural desire is to also think about synthetic data generation + finetuning to have your LLM "know" the data in its weights instead of just context windows.

TLDR: raw data from a given number of sources is collected, then compiled by an LLM into a .md wiki, then operated on by various CLIs by the LLM to do Q&A and to incrementally enhance the wiki, and all of it viewable in Obsidian. You rarely ever write or edit the wiki manually, it's the domain of the LLM. I think there is room here for an incredible new product instead of a hacky collection of scripts.

[📖 原文](https://nitter.net/karpathy/status/2039805659525644595#m)

[🔗 #0403-044221](#_0403-044221)

---

## 2026-03-31 13:23:32  {#_0331-132332}

🏷️ **[20260331](./tags/20260331.html)** 

New supply chain attack this time for npm axios, the most popular HTTP client library with 300M weekly downloads.

Scanning my system I found a use imported from googleworkspace/cli from a few days ago when I was experimenting with gmail/gcal cli. The installed version (luckily) resolved to an unaffected 1.13.5, but the project dependency is not pinned, meaning that if I did this earlier today the code would have resolved to latest and I'd be pwned.

It's possible to personally defend against these to some extent with local settings e.g. release-age constraints, or containers or etc, but I think ultimately the defaults of package management projects (pip, npm etc) have to change so that a single infection (usually luckily fairly temporary in nature due to security scanning) does not spread through users at random and at scale via unpinned dependencies.

More comprehensive article:
https://www.stepsecurity.io/blog/axios-compromised-on-npm-malicious-versions-drop-remote-access-trojan

[📖 原文](https://nitter.net/karpathy/status/2038849654423798197#m)

[🔗 #0331-132332](#_0331-132332)

---

## 2026-03-28 23:56:10  {#_0328-235610}

🏷️ **[20260328](./tags/20260328.html)** 

- Drafted a blog post
- Used an LLM to meticulously improve the argument over 4 hours.
- Wow, feeling great, it’s so convincing!
- Fun idea let’s ask it to argue the opposite. 
- LLM demolishes the entire argument and convinces me that the opposite is in fact true.
- lol

The LLMs may elicit an opinion when asked but are extremely competent in arguing almost any direction. This is actually super useful as a tool for forming your own opinions, just make sure to ask different directions and be careful with the sycophancy.

[📖 原文](https://nitter.net/karpathy/status/2037921699824607591#m)

[🔗 #0328-235610](#_0328-235610)

---

## 2026-03-27 00:10:52  {#_0327-001052}

🏷️ **[20260327](./tags/20260327.html)** 

When I built menugen ~1 year ago, I observed that the hardest part by far was not the code itself, it was the plethora of services you have to assemble like IKEA furniture to make it real, the DevOps: services, payments, auth, database, security, domain names, etc...

I am really looking forward to a day where I could simply tell my agent: "build menugen" (referencing the post) and it would just work. The whole thing up to the deployed web page. The agent would have to browse a number of services, read the docs, get all the api keys, make everything work, debug it in dev, and deploy to prod. This is the actually hard part, not the code itself. Or rather, the better way to think about it is that the entire DevOps lifecycle has to become code, in addition to the necessary sensors/actuators of the CLIs/APIs with agent-native ergonomics. And there should be no need to visit web pages, click buttons, or anything like that for the human. 

It's easy to state, it's now just barely technically possible and expected to work maybe, but it definitely requires from-scratch re-design, work and thought. Very exciting direction!

[📖 原文](https://nitter.net/karpathy/status/2037200624450936940#m)

[🔗 #0327-001052](#_0327-001052)

---

## 2026-03-26 00:22:08  {#_0326-002208}

🏷️ **[20260326](./tags/20260326.html)** 

R to @karpathy: (I cycle through all LLMs over time and all of them seem to do this so it's not any particular implementation but something deeper, e.g. maybe during training, a lot of the information in the context window is relevant to the task, so the LLMs develop a bias to use what is given, then at test time overfit to anything that happens to RAG its way there via a memory feature (?))

[📖 原文](https://nitter.net/karpathy/status/2036841069636370467#m)

[🔗 #0326-002208](#_0326-002208)

---

## 2026-03-26 00:05:14  {#_0326-000514}

🏷️ **[20260326](./tags/20260326.html)** 

One common issue with personalization in all LLMs is how distracting memory seems to be for the models. A single question from 2 months ago about some topic can keep coming up as some kind of a deep interest of mine with undue mentions in perpetuity. Some kind of trying too hard.

[📖 原文](https://nitter.net/karpathy/status/2036836816654147718#m)

[🔗 #0326-000514](#_0326-000514)

---

## 2026-03-25 00:56:24  {#_0325-005624}

🏷️ **[20260325](./tags/20260325.html)** 

Software horror: litellm PyPI supply chain attack. 

Simple `pip install litellm` was enough to exfiltrate SSH keys, AWS/GCP/Azure creds, Kubernetes configs, git credentials, env vars (all your API keys), shell history, crypto wallets, SSL private keys, CI/CD secrets, database passwords.

LiteLLM itself has 97 million downloads per month which is already terrible, but much worse, the contagion spreads to any project that depends on litellm. For example, if you did `pip install dspy` (which depended on litellm&gt;=1.64.0), you'd also be pwnd. Same for any other large project that depended on litellm.

Afaict the poisoned version was up for only less than ~1 hour. The attack had a bug which led to its discovery - Callum McMahon was using an MCP plugin inside Cursor that pulled in litellm as a transitive dependency. When litellm 1.82.8 installed, their machine ran out of RAM and crashed. So if the attacker didn't vibe code this attack it could have been undetected for many days or weeks.

Supply chain attacks like this are basically the scariest thing imaginable in modern software. Every time you install any depedency you could be pulling in a poisoned package anywhere deep inside its entire depedency tree. This is especially risky with large projects that might have lots and lots of dependencies. The credentials that do get stolen in each attack can then be used to take over more accounts and compromise more packages.

Classical software engineering would have you believe that dependencies are good (we're building pyramids from bricks), but imo this has to be re-evaluated, and it's why I've been so growingly averse to them, preferring to use LLMs to "yoink" functionality when it's simple enough and possible.

[📖 原文](https://nitter.net/karpathy/status/2036487306585268612#m)

[🔗 #0325-005624](#_0325-005624)

---

## 2026-03-21 08:55:37  {#_0321-085537}

🏷️ **[20260321](./tags/20260321.html)** 

Thank you Sarah, my pleasure to come on the pod! And happy to do some more Q&A in the replies.

[📖 原文](https://nitter.net/karpathy/status/2035158351357911527#m)

[🔗 #0321-085537](#_0321-085537)

---

*最后更新：2026-08-19T01:33:52.190Z*
