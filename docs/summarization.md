# Source-grounded summarization

Status: the architecture, validation, review workflow and evaluation harness are built and tested. **No AI model is connected and no summaries have been generated.** Connecting a provider means choosing a vendor, which costs money and needs approval.

## Principles

- Generated from one specific official bill version (`ai_summaries.source_document_id` and `source_content_hash`), never from a title or caption.
- Bill text is data, not instructions. It is wrapped in `<bill_text>` tags, and the system prompt tells the model to ignore any instructions inside it (`prompt.py`). An evaluation case checks for prompt injection.
- Structured output (`schema.py`): overview, key provisions, changes to existing law, affected groups (each marked `stated` or `inferred`), effective dates, fiscal information (only when an official fiscal note exists), and uncertainties. Every factual statement carries citations with an exact quote.
- Never presents proposed legislation as law. Never infers motives. Never recommends support or opposition.
- Clearly labeled as AI-generated in the interface, kept apart from official facts, and reportable by anyone.

## Lifecycle

```
generate ─► automated validation ─┬─ fails ─► rejected (never public)
                                  └─ passes ─► pending_review ─► human review ─┬─ approved ─► public
                                                                               └─ rejected
official text changes ─► approved/pending summaries for that version become superseded (trigger) ─► regenerate
```

Only `approved` summaries are visible to the public, enforced by RLS. A summary can be approved only if it passed validation and still matches the current official text (`pipeline.record_review`).

## Automated validation (`validate.py`)

| Check | Catches |
| --- | --- |
| `unknown_section` | Citations to sections that don't exist in this version |
| `quote_not_found` | Quotes that aren't in the official text (checked against the amended, current-law and raw readings) |
| `quote_wrong_section` | Real quotes attributed to the wrong section |
| `missing_citation` | Uncited factual statements, and "stated" effects without a citation |
| `presented_as_law` | "is now law", "now requires" and similar wording when the status isn't enacted |
| `not_neutral` | Advocacy ("you should support"), loaded labels ("common-sense bill") and motive language |
| `fiscal_without_source` (warning) | Fiscal claims when no official fiscal note exists |

Passing validation does **not** mean a summary is accurate. These checks catch mechanical failures. A reviewer still reads every summary against the official text.

## Human review

```bash
cd summarization
python -m civictexas_summarize pending
python -m civictexas_summarize show <summary-id>
python -m civictexas_summarize review <summary-id> --approve --notes "Checked each citation against SECTIONs 1-4"
python -m civictexas_summarize review <summary-id> --reject  --notes "Overstates who is affected"
```

Reviewers should check that each statement is supported by its cited section and that inferred effects are labeled. They should also confirm that nothing in the summary implies the bill is law, and that uncertainties are listed. Reader reports land in `content_reports` (`target_type = 'ai_summary'`).

## Evaluation dataset (`evals/cases.json`)

Three cases: two real 90R bill versions (HB 101, HB 103) and one clearly synthetic prompt-injection text. Each case has:

- `required_facts`: what any correct summary must convey. The accuracy score is the share of these facts covered by statements with valid citations.
- `candidates`: hand-written synthetic outputs, one reference summary plus failure modes (fabricated citation, invented quote, wrong section, "now law", advocacy, uncited statements, obeying injected instructions), each with its expected outcome.

```bash
cd summarization
python -m civictexas_summarize.evaluate              # checks the harness against prepared candidates
python -m civictexas_summarize.evaluate --provider X # scores a real model, once one is added
```

The current result: all 11 candidates behave as expected, both reference summaries score 1.0, and the "omits key facts" candidate scores 0.0 while passing the mechanical checks. That last case shows why human review is still required.

## Adding a provider

Implement `SummaryProvider.generate(prompt) -> str` in `providers.py` with the vendor's SDK, pass `prompt.json_schema` if the vendor supports structured output, and register it in `get_provider`. Put the API key in `SUMMARY_API_KEY` (server-side only). Then run the evaluation with `--provider` before generating anything for review.
