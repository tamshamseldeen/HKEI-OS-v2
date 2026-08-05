# HKEI OS v2 — LLM Generation Specification

## 1. Purpose

The LLM Generation layer receives:

- one `GenerationPrompt`
- one provider configuration
- one provider implementation

It returns one normalized generation result.

It does not:

- make editorial decisions
- modify facts
- rebuild prompts
- verify sources
- evaluate final quality
- approve publication
- generate SEO metadata

## 2. Input

The layer accepts exactly:

- one `GenerationPrompt`
- one LLM provider
- one generation configuration

## 3. Output

The layer returns one future object named `GenerationResult`.

It contains these fields:

- `content`
- `provider_name`
- `model_name`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `finish_reason`
- `request_id`
- `warnings`

Python types are not defined yet.

## 4. Provider-Agnostic Principle

- HKEI editorial logic must not depend on one provider.
- Provider adapters translate `GenerationPrompt` into provider-specific requests.
- Provider adapters normalize provider responses into `GenerationResult`.
- Core workflows must not import provider SDKs.
- Provider-specific errors must be converted into stable HKEI errors.
- Changing providers must not require redesigning editorial logic.

## 5. Provider Interface

Define one future interface named `LLMProvider` with one method:

```text
generate(
    prompt,
    configuration,
) → GenerationResult
```

Providers may include:

- OpenAI
- Anthropic
- Google
- local or self-hosted models
- future providers

Implementation is not defined yet.

## 6. Generation Configuration

Define one future object named `GenerationConfiguration`.

It contains these fields:

- `model`
- `max_output_tokens`
- `temperature`
- `timeout_seconds`
- `request_metadata`

Rules:

- `model` is provider-specific configuration.
- `temperature` may be unsupported by some models.
- Unsupported options must be rejected or ignored explicitly.
- Request metadata must not contain source content by default.
- API keys must not be stored in this object.

Python types are not defined yet.

## 7. Generation Result

`content`:

- final raw model output
- must remain unchanged before response parsing

`provider_name`:

- stable provider identifier

`model_name`:

- actual model used

`input_tokens`:

- integer when supplied by provider
- otherwise unavailable

`output_tokens`:

- integer when supplied by provider
- otherwise unavailable

`total_tokens`:

- integer when supplied or calculated safely
- otherwise unavailable

`finish_reason`:

- normalized completion status

`request_id`:

- provider request identifier when available

`warnings`:

- machine-readable generation warnings

## 8. Supported Finish Reasons

Use these exact values:

- `COMPLETED`
- `LENGTH_LIMIT`
- `CONTENT_FILTERED`
- `TOOL_CALL`
- `STOPPED`
- `UNKNOWN`

## 9. Required Generation Warnings

- `TOKEN_USAGE_UNAVAILABLE`
- `REQUEST_ID_UNAVAILABLE`
- `FINISH_REASON_UNKNOWN`
- `OUTPUT_EMPTY`
- `OUTPUT_TRUNCATED`
- `PROVIDER_OPTION_IGNORED`
- `PROVIDER_RESPONSE_INCOMPLETE`

Warnings may appear together.

## 10. Stable Generation Errors

Future implementations use these stable error codes:

- `PROVIDER_NOT_CONFIGURED`
- `API_KEY_MISSING`
- `MODEL_MISSING`
- `INVALID_GENERATION_CONFIGURATION`
- `PROVIDER_AUTHENTICATION_FAILED`
- `PROVIDER_PERMISSION_DENIED`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_QUOTA_EXCEEDED`
- `PROVIDER_TIMEOUT`
- `PROVIDER_CONNECTION_FAILED`
- `PROVIDER_REQUEST_REJECTED`
- `PROVIDER_RESPONSE_INVALID`
- `PROVIDER_INTERNAL_ERROR`
- `GENERATION_EMPTY`
- `GENERATION_INTERRUPTED`
- `UNKNOWN_PROVIDER_ERROR`

Errors must preserve the original exception as internal context when practical,
but must expose stable HKEI codes to callers.

## 11. Empty Output Policy

If the provider returns empty or whitespace-only content:

- Generation must fail with `GENERATION_EMPTY`.
- The system must not fabricate replacement content.
- The system must not treat empty output as a successful generation.

## 12. Truncation Policy

If the finish reason is `LENGTH_LIMIT`:

- Preserve returned content.
- Add `OUTPUT_TRUNCATED`.
- Do not silently continue generation in the MVP.
- Do not combine multiple model calls automatically.
- Downstream review must detect that the result may be incomplete.

## 13. Retry Policy

For the first MVP:

- No automatic retry inside provider adapters.
- Retry orchestration belongs to a future workflow layer.
- Authentication, permission, quota, and invalid-request errors must not be
  retried automatically.
- Timeout, rate-limit, and connection errors may become retryable in a future
  implementation.
- Provider adapters must return or raise stable errors immediately.

## 14. Token Usage

- Token values are informational.
- Token usage must not affect editorial content.
- Missing usage data must not fail generation.
- Missing values produce `TOKEN_USAGE_UNAVAILABLE`.
- Token fields may be unavailable when providers do not supply them.
- Token counts must never appear inside generated article content.

## 15. Request Metadata

- Request metadata is operational metadata only.
- It may include workflow ID or environment name.
- It must not include API keys.
- It should not include full article source content.
- It must not alter prompt content.
- It must not be sent when unsupported unless explicitly configured.

## 16. Security

- API keys come from secure runtime configuration.
- API keys must never appear in logs, prompts, exceptions, or results.
- Prompt content may contain sensitive source material.
- Provider adapters must not log full prompt content by default.
- Provider request IDs may be stored for debugging.
- Provider responses must be treated as untrusted until parsed and reviewed.

## 17. Determinism

- Identical prompts may still produce different provider outputs.
- Prompt construction remains deterministic.
- Provider response generation is not guaranteed deterministic.
- Temperature should default to a conservative value in future implementations.
- HKEI must not claim deterministic model output.

## 18. Provider Adapter Responsibilities

A provider adapter must:

- validate required provider configuration
- convert `GenerationPrompt` into provider request format
- submit the request
- map provider response fields
- normalize finish reason
- normalize token usage
- map provider errors
- return `GenerationResult`
- avoid modifying prompt content

A provider adapter must not:

- add editorial instructions
- remove safety instructions
- rewrite source content
- change article strategy
- retry silently
- parse the article
- evaluate quality

## 19. Core Generation Service

Define one future service named `GenerationService`.

Responsibilities:

- receive `GenerationPrompt`
- receive provider and configuration
- call provider exactly once
- return `GenerationResult` unchanged
- propagate stable generation errors

It must not contain provider SDK code.

## 20. Output Parsing Boundary

- `GenerationResult.content` remains raw model output.
- Markdown validation and article parsing belong to the next layer.
- The generation layer must not remove model commentary.
- The generation layer must not fix malformed Markdown.
- The generation layer must not rewrite article content.

## 21. Logging Policy

For the MVP, allowed logs are:

- provider name
- model name
- request status
- request duration
- token counts when available
- stable error code
- request ID when available

Do not log by default:

- API key
- full system prompt
- full user prompt
- full source material
- full generated content
- private metadata

Logging implementation is outside the first task.

## 22. Non-Goals

- No prompt construction
- No editorial planning
- No fact extraction
- No article parsing
- No Markdown validation
- No quality evaluation
- No SEO generation
- No publication decision
- No automatic retries
- No multi-provider fallback
- No streaming output
- No tool calling
- No image generation
- No web browsing

## 23. MVP Scope

For the first MVP:

- Define one `LLMProvider` interface.
- Define one `GenerationConfiguration`.
- Define one `GenerationResult`.
- Implement one provider adapter later.
- Call the provider once.
- Return normalized content and metadata.
- Use non-streaming generation.
- Do not retry automatically.
- Do not parse or evaluate the output.

## 24. Acceptance Criteria

The future implementation must:

- receive one `GenerationPrompt`
- receive one provider
- receive one generation configuration
- call the provider exactly once
- return exactly one `GenerationResult`
- preserve raw model content
- normalize provider and model metadata
- normalize finish reason
- preserve token usage when available
- return warnings when metadata is unavailable
- reject empty output
- expose stable error codes
- avoid provider SDK imports in core workflows
- avoid API keys in models and logs
- make no editorial decisions
