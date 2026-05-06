# Nostr Skill for Hermes Agent

## Description
Complete, secure Nostr integration for Hermes Agent. Read events, draft posts, upload images to Blossom, publish with explicit TTY approval. NIP-94 compliant image metadata.

## Meta-Data
- version: 2.1.0
- author: "bronoman + SuperGrok + Hermes local (May 2026)"
- license: MIT
- github: https://github.com/bronoman/hermes-skills/tree/3507d9bc4b1538bee6ec62acaba2166fbd21d94a/social-media/nostr
- platforms: [linux]

## What This Skill Does

**Read Operations (No Private Key Required)**
- ✅ Fetch recent Nostr events (text notes, kind 1) from multiple relays
- ✅ Query relays with NIP-01 filters (by kind, timestamp, author, content)
- ✅ Parse and deduplicate events from multiple relay sources
- ✅ Display events in JSON or formatted text
- ✅ Handle relay connectivity failures gracefully with fallback relays

**Draft Operations (No Private Key Required)**
- ✅ Create unsigned Nostr events in JSON format
- ✅ Attach images via image server or blossom server
- ✅ Specify event kind, content, and tags (threading, replies)
- ✅ Review drafts before any cryptographic commitment
- ✅ Edit draft JSON before publishing

**Publish Operations (With Private Key + User Approval)**
- ✅ Sign events with secp256k1 cryptography using nsec private key
- ✅ Decode bech32-encoded nsec to 32-byte private key (with 33-byte checksum fix)
- ✅ Broadcast signed events to multiple relays for redundancy
- ✅ Require explicit user confirmation ("YES") before any signing
- ✅ Return event_id and verification URLs (Primal, Damus, etc.)

**Cryptographic Operations**
- ✅ Validate bech32 nsec format and derive public key (npub)
- ✅ Sign events with ECDSA (secp256k1 curve, NIP-01 standard)
- ✅ Handle multi-relay distribution with connection timeouts
- ✅ Verify event signatures are cryptographically valid

## Documentation
see references/DESCRIPTION.md file for additional details

## Author Notes

This skill represents the complete, production-ready Nostr integration for Hermes Agent. Every operation is:
- **Cryptographically verifiable** (NIP-01 compliant)
- **Audit-logged** (timestamps on all operations)
- **Secure by default** (approval gates, env var isolation)
- **Network-resilient** (multi-relay, automatic fallback)

The 33-byte checksum discovery solved a critical blocker; once identified, the fix is trivial but essential. Trust the cryptography, not the relay or third party. Read first, sign last, always ask before publish.

**Philosophy:** Nostr is social media that respects your autonomy. This skill brings that philosophy to Hermes.

PRs welcome.

## Legal Disclaimer
This Nostr skill and associated code etc. is provided for educational, experimental, and artistic purposes only.
The code is offered "as is", without any warranty of any kind. Use of this skill is entirely at your own risk.
The author is not responsible or liable for:
- Any content you publish using this skill
- Any actions, consequences, or damages resulting from its use
- Any interaction with Nostr relays, Telegram, or third-party services

This project is an expression of personal technical exploration and free speech. It does not constitute professional software, financial advice, or legal counsel.
By using this skill you agree that you are solely responsible for your own actions and compliance with all applicable laws.
