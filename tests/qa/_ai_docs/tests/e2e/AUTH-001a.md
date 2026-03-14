# AUTH-001a: Anonymous Mode — Private Channel Denial

Verify anonymous user gets explicit 403 error (not 404 or silent fallback) when accessing private channels.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Private Channels](../../AUTH_SETUP.md#prerequisites-logged-out--private-channels-auth-001a) | Auth state configured | | + |
| 1 | "Create environment anon-test with Python 3.11" | HTTP 403 Forbidden | | + |
| Post | [Cleanup](../../AUTH_SETUP.md#post-conditions--cleanup) | State restored | | + |

## Expected Error

- HTTP 403 Forbidden on `repo.anaconda.cloud`
- Error message: "You do not have permission to access this resource"
- **NOT** 404 (would indicate wrong URL routing)
- **NOT** silent fallback to public channel

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Blocked by DESK-1358 (URL routing) |
| RC2 | Unblocked — URL routing fixed; anonymous users correctly get 403 |
