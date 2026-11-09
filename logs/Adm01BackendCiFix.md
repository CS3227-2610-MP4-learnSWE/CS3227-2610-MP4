# ADM-01 backend CI fix ? 2026-11-10

Developer maintenance from supplied CI trace; no tests executed at user request.

Startup health checks now call the actual local model directly, so monkeypatched scanner functions cannot race with warmup or receive an extra health-fixture call. The real-model smoke suite uses one clean subprocess, isolated from earlier tests that intentionally leave the shared scanner unhealthy until restart. Name recognition, provisioning, timing assertions and the narrow Windows policy skip remain intact; no Linux skip or weakened privacy fallback added.
