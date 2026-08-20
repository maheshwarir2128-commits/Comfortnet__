"""
ComfortNet backend configuration.

DEVELOPMENT CHOICE: Settings are read from environment variables with
development-friendly defaults (SQLite file DB, permissive CORS). None of
these defaults are appropriate for a production deployment; they exist so
the Phase 2 software foundation is runnable for a hackathon demo without
extra setup. Production configuration (real DB engine, real secrets
management, restricted CORS) is explicitly out of scope for Phase 2.
"""
import os

# --- Database ---
# DEVELOPMENT CHOICE: SQLite file DB for local/demo use only. The Phase 2
# Architecture Specification deliberately left the production DB engine
# undecided (see §7 of the spec) — this is NOT that decision, just a
# convenient default for running the prototype backend.
DATABASE_URL = os.getenv("COMFORTNET_DATABASE_URL", "sqlite:///./comfortnet_dev.db")

# --- CORS ---
# DEVELOPMENT CHOICE: allow all origins so the static HTML prototype
# (opened as a local file or served from any port) can call this API
# during development/demo. Must be restricted before any real deployment.
CORS_ALLOW_ORIGINS = os.getenv("COMFORTNET_CORS_ORIGINS", "*").split(",")

# --- Auth (placeholder only — see app/routers/auth.py) ---
# THIS IS NOT REAL AUTHENTICATION. There is no password hashing, no token
# signing, no expiry enforcement. It exists only so /auth/* returns a
# structured response instead of a 404, per Phase 2 Step 4's instruction
# to return an explicit placeholder rather than pretend something works.
DEV_PLACEHOLDER_TOKEN = "dev-placeholder-token-not-secure"

# --- Simulated telemetry ---
# Marks every telemetry row inserted by the simulator (or by anyone POSTing
# to /telemetry today, since no real hardware exists) so the data source is
# always traceable in the database itself, not just in UI copy.
TELEMETRY_SOURCE_SIMULATED = "simulated"
