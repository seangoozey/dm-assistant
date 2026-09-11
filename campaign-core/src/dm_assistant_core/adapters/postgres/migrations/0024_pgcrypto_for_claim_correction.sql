-- Migration 0023 uses digest() to bind an immutable proposal version to its payload.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
