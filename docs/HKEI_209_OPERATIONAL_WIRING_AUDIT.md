# HKEI-209 operational wiring audit

Status: `OPERATIONAL_WIRING_COMPLETE`

The controlled canary has one strict request-local mode source, defaults to
`SHADOW`, consumes explicit stop recommendations through that source, records a
sanitized idempotent observation before consumption, and routes authority only
to `INTERNAL_TOPIC_AUTHORITY_CANARY_PATH`. Configuration, sink, and consumer
failures preserve the deterministic Topic. The public result contains four-way
Topic provenance and no raw source, request, provider, credential, or reasoning
payload. Global authority remains disabled; Format and Reader Intent have no
authority path. Verification uses fake providers only.
