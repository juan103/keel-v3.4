# PRECHECK PROMPT

Paste this into a fresh Claude session (claude.ai or Claude Code, doesn't matter which). After Claude responds with the interrogation questions, paste your answers. The final output goes into `goals/GOALS.md` of your new project.

---

## THE PROMPT

```
You are helping me turn a rough idea into a structured plan that an AI coding agent can execute well. Do not write code. Do not start building. Your only job is to interrogate the idea until it is buildable.

I will describe the idea. You will respond in this order:

1. RESTATE — In two sentences, tell me what you think I'm trying to build and what question or goal it serves. If you're guessing, say so.

2. CLASSIFY — Is this exploration (we don't yet know if it can work / what the answer is) or building (we know what we want, we need it built)? These need different plans. If exploration, the falsifier phase below is non-negotiable.

3. INTERROGATE — Ask me 3 to 7 questions whose answers most constrain the build. Prioritize:
   - What counts as success
   - What would falsify the idea
   - What frames I'm committing to
   - What I'm leaving out
   - What arbitrary choices will have to be made
   Don't ask me anything you can reasonably infer.

4. WAIT — Stop here. Do not proceed until I answer.

After I answer, produce the GOALS.md content with these sections:

5. CLAIM — One paragraph. What we're testing or building, in plain language.

6. SUCCESS CRITERIA — How will we know it worked? Be measurable. If exploration, what would count as a meaningful negative result?

7. FALSIFIER — The single experiment or test whose failure means we stop the whole project. This is the most important section. If this is exploration and you cannot name a falsifier, the project is not ready to start.

8. COMMITMENTS — Numbered list of load-bearing decisions implied by my answers. Each one in one sentence. These will become the first ADRs.

9. NON-COMMITMENTS — What I'm explicitly leaving open or deferring. Name them so they don't get silently decided later.

10. PHASES — A short ordered list of gates. Each phase has: name, what gets built, what gets verified, what would trigger killing the phase. The falsifier phase comes early, not late.

11. RISKS — The 3 most likely ways this build fails or produces a misleading result. Be specific. "Bugs" is not a risk.

Be direct. Push back if the idea has a hidden contradiction or if the success criteria are not measurable. Do not be encouraging by default. If I can't answer your interrogation questions, say so and tell me what to think about before continuing.
```

---

## HOW TO USE

1. Paste the prompt above into a fresh Claude session.
2. After Claude responds, paste your project idea (one paragraph is enough).
3. Answer the interrogation questions Claude asks.
4. Copy the output (sections 5–11) into `goals/GOALS.md` of your new project folder, plus add a `## Lineage` section pointing to the document(s) the precheck operated on.
5. Now you can open Claude Code with the rest of the kit in place.

If Claude rushes past the interrogation step, push back: "Stop. Do step 3 properly. Ask me harder questions."

If Claude lets you skip naming a falsifier on an exploration project, push back: "We don't proceed without a falsifier."

---

## v3 ADDITIONAL STEPS

After producing `goals/GOALS.md`, three additional steps run before any phase work or commitment artifact (OTS stamp, public registration). These steps catch the project-killing friction beliefwire surfaced.

### Step A — Reachability declaration (v3.SPINE.B)

List every external dependency the project requires at execution time (data sources, APIs, calendar servers, etc.). Declare a typed probe for each in `goals/reachability.md` (template at the kit root). Run the probe set via `python preflight.py --strict` (v3.3: strict mode runs probes live and blocks on failure; plain `preflight.py` is the cached session mode). If any probe fails (e.g., geo-block, deprecated endpoint, paywall), do not proceed — see the file for resolution paths.

This catches: regulatory geo-blocks, deprecated endpoints, paywalls, auth walls, schema drift at the URL level, ISP-side filtering, captive portals, DNS hijacking, and substrate-side service deprecation. All at Gate 0, before pre-registration is committed.

### Step B — Adversarial review handoff (v3.SPINE.C)

If the project will pre-register binding parameters (i.e., will adopt a `keel-binding` block in its binding ADR), run `ADVERSARIAL_REVIEW_PROMPT.md` against at least two parallel AI sessions in *different* model families. Compile the catches and dispositions into `pre-stamp-review.md` (template at kit root). Commit it before OTS-stamp (or equivalent).

Per ADR-0007: the kit ships the prompt; running it is the user's discipline. The kit verifies *presence* of `pre-stamp-review.md` in `post_stamp` state, not its quality. Quality is on you.

### Step C — Environment portability checklist (v3.DOC.3)

For projects with non-trivial pre-stamp tooling dependencies (OpenTimestamps, GPG, hardware tokens, etc.), verify each dependency runs end-to-end on the *target* environment (the same machine where the actual stamp will happen, not a test VM). Record the results in `goals/environment.md` (optional template). Document any wrappers or workarounds with explicit boundaries (what the wrapper does, what it does NOT change about the stamped artifact).

This catches the class of friction beliefwire hit at OTS-stamp time (Python 3.13 + OpenSSL 3 + python-bitcoinlib transitive failure, not discovered until 90 minutes into the stamp procedure).
