# Keel Binding ADR

**Status:** accepted

## Context

This binding ADR records the frame validity audit for the adversarial-exercise
fixture. The frame validity audit assesses whether the project inferential claim
can be expressed using the declared machinery requirements.

## Frame Validity

```keel-binding
type = "frame_validity"
id = "frame-validity.primary"
inferential_claim = "The silent-path defense distance exceeds 1.0 under all evaluated configurations."
machinery_requirements = "keel_v3.4 engine: silent_path_defense_distance, GP-6 baseline-isolation"
audit_artifact = "audit/frame_validity_audit.json"
author_verdict = "APPROVED"
dispositions = ["APPROVED"]
```
