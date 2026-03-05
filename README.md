# h1spec

HTTP/1.1 conformance testing tool, in the spirit of [h2spec](https://github.com/summerwind/h2spec).

Point it at any HTTP server to verify RFC 9112/9110 compliance.

## Usage

```sh
# Run against a server
uvx --from git+https://github.com/dropseed/h1spec h1spec localhost:8000

# Strict mode (includes edge-case tests)
h1spec --strict localhost:8000

# Skip hardening checks
h1spec --no-hardening localhost:8000

# Run specific sections
h1spec --section headers --section body localhost:8000
```

## Test sections

- **Request Line** (RFC 9112 S3) — method, target forms, version
- **Headers** (RFC 9112 S5) — Host validation, header syntax
- **Body** (RFC 9112 S6-7) — chunked encoding, Content-Length, Expect
- **Response Semantics** (RFC 9110) — HEAD, error delimiting
- **Connection** (RFC 9112 S9) — keep-alive, close
- **Hardening** — oversized requests, header floods

## Limitations

h1spec is inspired by [h2spec](https://github.com/summerwind/h2spec), but HTTP/1.1 is a fundamentally harder protocol to conformance-test. Here's what that means for you:

### Passing doesn't guarantee correctness

h1spec checks that your server returns the right status codes for various good and bad inputs. But it can only see the response — it can't see *how* your server parsed the request internally. A server that returns 400 for the wrong reason will still pass. A server that silently accepts malformed input (and happens to return 200) will fail the test, even though the silent acceptance is the real bug. **Treat passing tests as a good signal, not proof of compliance.**

### Failing doesn't always mean your server is wrong

Some RFC 9112 requirements use SHOULD rather than MUST, meaning servers are allowed to handle things differently. The `--strict` flag controls these edge cases — without it, h1spec only tests MUST-level requirements. If a test fails in non-strict mode, your server likely has a real issue. If it only fails in `--strict` mode, it may just be a different (valid) interpretation.

### Some important things can't be tested at all

- **Request smuggling** — the most dangerous real-world HTTP/1.1 issue — happens when a proxy and backend disagree on where one request ends and the next begins. h1spec talks directly to your server, so it can verify the building blocks (rejecting ambiguous Transfer-Encoding + Content-Length, etc.) but can't test actual smuggling scenarios. You need proxy-chain testing for that.
- **Pipelining** — sending multiple requests without waiting for responses is part of HTTP/1.1, but server support is too inconsistent to test reliably. These tests were removed.
- **Proxy behavior** — if your server acts as a proxy/intermediary, h1spec can't test forwarding rules, hop-by-hop header stripping, Via headers, or other intermediary requirements.

### No TLS support

h1spec connects over plain TCP. If your server only listens on HTTPS, you'll need to put a TLS-terminating proxy in front of it or expose a plain HTTP port for testing.

### Some tests are timing-sensitive

h1spec uses a 5-second socket timeout. If your server is slow to respond (e.g. under load, or blocking on something), it may look like "no response" and fail. If you see flaky results, try running against an idle server.

### The test technique has a quirk

Most tests send a request and then immediately half-close the TCP connection (signaling "I'm done sending"). Some servers behave differently when they see this — they may skip reading the body or close the connection earlier than they normally would. If a test fails unexpectedly, this could be why. The keep-alive and connection tests use a different technique to avoid this.

## Credits

This was primarily written for use testing [Plain](https://github.com/dropseed/plain).

Most of the code was written by [Codex](https://openai.com/index/codex/) and [Claude](https://claude.ai/).
