# AUTH-001a: Anonymous Mode — Private Channel Denial

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

Verify anonymous user gets explicit denial (not 404 or silent fallback) when accessing private channels.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Private Channels](./setup/AUTH_SETUP.md#prerequisites-logged-out--private-channels-auth-001a) | Auth state configured | | + |
| 1 | "Create environment anon-test with Python 3.11" | Auth error (see below) | | + |
| Post | [Cleanup](./setup/AUTH_SETUP.md#cleanup-interactive-login) | State restored | | + |

## Expected Error

Either of these errors is acceptable — both correctly deny access to anonymous users:

**Option A: Token not found (client-side check)**
```json
{
  "is_error": true,
  "error_description": "There was an error while creating the environment. Details: ('conda', 'Token not found for defaults. Please install token with `anaconda token install`.')",
  "tool_result": {}
}
```
This occurs when `anaconda-auth` plugin checks for repo token locally before making HTTP request.

**Option B: HTTP 403 Forbidden (server-side check)**
- Error message: "You do not have permission to access this resource"
- This occurs when request reaches `repo.anaconda.cloud` without valid credentials.

## Pass Criteria

- ✅ Access denied with clear error message
- ❌ **NOT** 404 (would indicate wrong URL routing)
- ❌ **NOT** silent fallback to public channel
- ❌ **NOT** successful environment creation

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Blocked by DESK-1358 (URL routing) |
| RC2 | Unblocked — URL routing fixed; anonymous users correctly denied |
