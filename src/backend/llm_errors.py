"""Map shared-client failures to the teacher generation API errors."""
from errors import ApiError
from llm_client import (
    LlmBadResponse, LlmBusy, LlmError, LlmInputTooLarge, LlmNotConfigured,
    LlmRateLimited, LlmTimeout, LlmUpstreamError,
)


def generation_error(exc: LlmError) -> ApiError:
    if isinstance(exc, LlmRateLimited):
        return ApiError(429, "llm_rate_limited", "Too many generation requests. Please wait before retrying.", retry_after_seconds=exc.retry_after_seconds)
    if isinstance(exc, LlmBusy):
        return ApiError(429, "llm_busy", "The AI service is busy. Please wait before retrying.", retry_after_seconds=exc.retry_after_seconds)
    if isinstance(exc, LlmNotConfigured):
        return ApiError(503, "llm_not_configured", "The AI service is not configured.")
    if isinstance(exc, LlmInputTooLarge):
        return ApiError(422, "source_text_too_large", "The source cannot fit the AI request limit. Choose a shorter source.")
    if isinstance(exc, LlmTimeout):
        return ApiError(504, "llm_timeout", "Generation timed out. Please try again.")
    if isinstance(exc, LlmUpstreamError):
        return ApiError(502, "llm_upstream_error", "The AI service could not generate content. Please try again.")
    if isinstance(exc, LlmBadResponse):
        return ApiError(502, "llm_bad_response", "The AI service returned unusable content. Please try again.")
    return ApiError(503, "llm_unavailable", "The AI service is unavailable. Please try again later.")
