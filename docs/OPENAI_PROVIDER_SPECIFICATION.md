# HKEI OS v2 — OpenAI Provider Specification

## 1. Purpose

The OpenAI provider adapter:

- receives one `GenerationPrompt`
- receives one `GenerationConfiguration`
- submits one non-streaming request to OpenAI
- returns one normalized `GenerationResult`
- maps OpenAI errors to stable HKEI generation errors

It does not:

- make editorial decisions
- modify the prompt
- rewrite source content
- evaluate article quality
- parse Markdown
- retry automatically
- select a different provider

## 2. Provider Name

Use this exact stable provider name:

`OPENAI`

## 3. SDK

The adapter uses the official OpenAI Python SDK.

It uses the Responses API. It does not use Chat Completions in the MVP.

## 4. Input Mapping

- `GenerationPrompt.system_prompt` → OpenAI system instruction
- `GenerationPrompt.user_prompt` → OpenAI user input
- `GenerationConfiguration.model` → `model`
- `GenerationConfiguration.max_output_tokens` → `max_output_tokens`
- `GenerationConfiguration.temperature` → `temperature` only when supported
- `GenerationConfiguration.timeout_seconds` → client or request timeout
- `GenerationConfiguration.request_metadata` → `metadata` only when supported
  and explicitly enabled

The adapter must not alter prompt text.

## 5. Request Shape

The adapter must call:

```text
client.responses.create(...)
```

The request must include:

- `model`
- `instructions`
- `input`
- `max_output_tokens`

Temperature is optional. Metadata is optional.

The adapter must not:

- include provider-specific tools
- enable web search
- enable file search
- enable code execution
- use streaming

## 6. Response Content

Use the normalized text output exposed by the SDK. Prefer:

`response.output_text`

If it is unavailable, treat the response as invalid. Do not reconstruct content
from unsupported internal structures in the MVP.

## 7. Token Usage Mapping

When available, map:

- `input_tokens`
- `output_tokens`
- `total_tokens`

If usage is unavailable, set the token fields to `None` and add:

`TOKEN_USAGE_UNAVAILABLE`

Generation must not fail only because usage is unavailable.

## 8. Finish Reason Mapping

Map provider completion status to:

- `COMPLETED`
- `LENGTH_LIMIT`
- `CONTENT_FILTERED`
- `TOOL_CALL`
- `STOPPED`
- `UNKNOWN`

Mapping rules:

- completed → `COMPLETED`
- incomplete because max output tokens → `LENGTH_LIMIT`
- safety or refusal filtering → `CONTENT_FILTERED`
- tool-related termination → `TOOL_CALL`
- explicitly stopped → `STOPPED`
- unrecognized status → `UNKNOWN`

When the result is `UNKNOWN`, add:

`FINISH_REASON_UNKNOWN`

## 9. Request ID

Use the provider response request identifier when available.

If it is unavailable, set `request_id` to `None` and add:

`REQUEST_ID_UNAVAILABLE`

## 10. Empty Output

If `response.output_text` is `None`, empty, or whitespace-only, raise:

`GenerationError("GENERATION_EMPTY")`

Do not return an empty `GenerationResult`.

## 11. Truncation

When the mapped finish reason is `LENGTH_LIMIT`:

- preserve returned content
- add `OUTPUT_TRUNCATED`
- do not continue generation
- do not make a second request

## 12. Response Validation

Treat the response as invalid when:

- the response object is missing
- the `output_text` attribute is unavailable
- the model identifier cannot be determined
- the provider response shape is unsupported

Raise:

`PROVIDER_RESPONSE_INVALID`

## 13. Error Mapping

- OpenAI authentication errors → `PROVIDER_AUTHENTICATION_FAILED`
- permission errors → `PROVIDER_PERMISSION_DENIED`
- rate-limit errors → `PROVIDER_RATE_LIMITED`
- insufficient quota errors → `PROVIDER_QUOTA_EXCEEDED`
- timeout errors → `PROVIDER_TIMEOUT`
- connection errors → `PROVIDER_CONNECTION_FAILED`
- invalid or rejected requests → `PROVIDER_REQUEST_REJECTED`
- server-side provider errors → `PROVIDER_INTERNAL_ERROR`
- all unknown OpenAI errors → `UNKNOWN_PROVIDER_ERROR`

Preserve the original exception in `GenerationError.original_exception`. Do not
expose the original exception text in the public message.

## 14. Configuration Validation

Before the request:

- If the API key is missing, raise `API_KEY_MISSING`.
- If the model is empty, raise `MODEL_MISSING`.
- If `max_output_tokens <= 0`, raise `INVALID_GENERATION_CONFIGURATION`.
- If `timeout_seconds <= 0`, raise `INVALID_GENERATION_CONFIGURATION`.
- If temperature is not `None` and outside the supported range, raise
  `INVALID_GENERATION_CONFIGURATION`.

Do not validate editorial content here.

## 15. API Key

The provider constructor may receive:

`api_key: str`

Rules:

- The API key must not be stored in `GenerationConfiguration`.
- The API key must not appear in repr output.
- The API key must not appear in exceptions.
- The API key must not be logged.
- A missing or whitespace-only key is invalid.

## 16. Client Injection

The adapter should support injecting an OpenAI client for tests. This allows:

- unit tests without network calls
- deterministic response fixtures
- error mapping tests

When no client is supplied, create an official OpenAI client using the API key.

## 17. Provider Contract

The provider must implement:

```text
LLMProvider.generate(
    prompt,
    configuration,
) -> GenerationResult
```

It must:

- call OpenAI once
- return one `GenerationResult`
- preserve raw output content
- normalize metadata
- map errors
- avoid retries
- avoid prompt modification

## 18. Warnings

Supported provider warnings:

- `TOKEN_USAGE_UNAVAILABLE`
- `REQUEST_ID_UNAVAILABLE`
- `FINISH_REASON_UNKNOWN`
- `OUTPUT_TRUNCATED`
- `PROVIDER_OPTION_IGNORED`
- `PROVIDER_RESPONSE_INCOMPLETE`

Preserve warning order and remove duplicates.

## 19. Security

- Never log API keys.
- Never log full prompts by default.
- Never expose OpenAI exception text to callers.
- Treat provider output as untrusted.
- Do not send source data outside the configured prompt.
- Do not add hidden provider instructions.

## 20. Non-Goals

- No streaming
- No retries
- No multi-provider fallback
- No tool calls
- No web search
- No file search
- No image generation
- No response parsing
- No quality evaluation
- No prompt rewriting
- No environment loading inside the provider

## 21. MVP Scope

For the first implementation:

- One non-streaming Responses API call
- One model
- One API key
- One `GenerationPrompt`
- One `GenerationConfiguration`
- One `GenerationResult`
- Injected client support
- Unit tests with mocked responses
- No real network calls in tests

## 22. Acceptance Criteria

The future implementation must:

- implement `LLMProvider`
- accept API key or injected client
- validate configuration
- call `responses.create` exactly once
- pass model, instructions, input, and `max_output_tokens`
- pass optional temperature only when present
- return normalized `GenerationResult`
- preserve output text
- normalize token usage
- normalize finish reason
- normalize request ID
- add warnings when metadata is unavailable
- reject empty output
- map OpenAI errors to stable `GenerationError` codes
- preserve original exceptions internally
- make no network calls in unit tests
