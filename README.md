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
- **Connection** (RFC 9112 S9) — keep-alive, pipelining, close
- **Hardening** — oversized requests, header floods

## Credits

Most of this was written by [Codex](https://openai.com/index/codex/) and [Claude](https://claude.ai/).
