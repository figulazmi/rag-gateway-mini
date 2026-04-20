---
id: 2026-04-19-sdl-stale-token-infinite-loop-fix-loginr-001
date: 2026-04-19
source: claude-code-cli
collection: knowledge_v2
project: petrochina-eproc
chunk_type: debug
topic: SDL stale token infinite loop fix Login.razor LogoutKicked
tags: [petrochina, eproc, sdl, authentication, blazor, localstorage, session-kicked, infinite-loop]
related: []
session_type: 
environment: dev
git_branch: 
status: implemented
chunk_source: code
supersedes: 
superseded_by: 
---

## CHUNK 1: SDL stale token infinite loop fix Login.razor LogoutKicked

### Context
PetroChina.Eproc Blazor WASM project. Single Device Login (SDL) fully implemented: UserController sends SignalR SessionKicked, SessionValidationMiddleware returns 401 + X-Session-Kicked header, HttpRequestHelper detects header and calls LogoutKicked(). Branch: fix/sdl-stale-token-auto-invalidate, PR #10, Issue #9.

### Problem
Two bugs caused stale token to not auto-redirect to login page, requiring manual localStorage clear:
1. Login.razor.cs OnInitializedAsync called DoRedirect() even when reason=kicked, causing infinite redirect loop if BitzArt auth state was not fully cleared before NavigateTo fired.
2. LogoutKicked() and LogoutKickedBy() in TokenService only cleared cookies (BaseApiUrl, UserSessionInfo) but not Blazored localStorage, so menu cache and other UI state persisted across the redirect loop.

### Solution
Fix 1 - Login.razor.cs (Internal + External): Add early return when reason=kicked to break the loop.
Fix 2 - TokenProvider.cs (Internal + External): Inject ILocalStorageService (Scoped, already registered via AddBlazoredLocalStorage), call ClearAsync() before cookie removal in LogoutKicked and LogoutKickedBy.

### Key Facts
- UserController.Login ALREADY sends SignalR SessionKicked after successful login - no backend change needed
- SessionKickListenerService.cs ALREADY exists in Services/General/ (Internal) and Services/ (External) - client already subscribes to hub
- Login page OnInitializedAsync must guard: if (Reason == "kicked") return; BEFORE auth state check
- TokenService is registered as Scoped (AddScoped<ITokenService, TokenService>) - safe to inject ILocalStorageService (also Scoped)
- LogoutKicked() and LogoutKickedBy() must call await _LocalStorage.ClearAsync() as first step before cookie removal
- Login.razor.cs OnAfterRenderAsync already calls ClearAsync() BUT it never runs during the infinite loop since redirect fires first
- Build result: 0 errors, 0 new warnings after fix

### Code
```csharp
// Login.razor.cs (Internal + External) - OnInitializedAsync
protected override async Task OnInitializedAsync()
{
    await base.OnInitializedAsync();
    if (Reason == "kicked") return; // ADDED: break infinite redirect loop

    var authState = await _UserService.GetAuthenticationStateAsync();
    var isAuth = authState.User.Identity?.IsAuthenticated ?? false;
    if (isAuth)
        DoRedirect();
}

// TokenProvider.cs (Internal + External) - TokenService constructor + methods
private readonly ILocalStorageService _LocalStorage; // ADDED field

public TokenService(IUserService userService, ICookieService cookieService,
    NavigationManager navManager, ILocalStorageService localStorageService) // ADDED param
{
    _LocalStorage = localStorageService;
}

public async Task LogoutKicked()
{
    await _LocalStorage.ClearAsync(); // ADDED - clear before cookie removal
    await _CookieService.RemoveAsync(CookieKey.BaseApiUrl);
    await _CookieService.RemoveAsync(CookieKey.UserSessionInfo);
    await _UserService.SignOutAsync();
    _NavManager.NavigateTo("/Account/Login?reason=kicked", true);
}
```

## CHUNK 2: SDL TokenService NullRef and JSDisconnectedException on session expiry

### Context
Blazor Server (Internal.App.Client). TokenService in TokenProvider.cs handles auth cookies and session management. Called on every page render via MainLayout and MainContent OnAfterRenderAsync.

### Problem
Two cascading errors on session expiry/kick:
1. NullReferenceException at TokenProvider.cs:49 in GetToken() -- `baseApiUrlCookie.Value` throws when cookie is missing (auth state says authenticated but BaseApiUrl cookie was cleared).
2. JSDisconnectedException in Logout/LogoutKicked -- circuit already dead from error 1, so SignOutAsync and NavigateTo fail.

### Solution
Two targeted fixes in TokenProvider.cs:
1. Null-check `baseApiUrlCookie` before accessing `.Value` in GetToken():
   ```csharp
   if (baseApiUrlCookie == null) { await Logout(); return (null, null); }
   ```
2. Wrap all JS-interop calls in Logout/LogoutKicked/LogoutKickedBy with try-catch JSDisconnectedException:
   ```csharp
   try { await _UserService.SignOutAsync(); } catch (JSDisconnectedException) { }
   try { _NavManager.NavigateTo(...); } catch (JSDisconnectedException) { }
   try { await _LocalStorage.ClearAsync(); } catch (JSDisconnectedException) { }
   ```
Also add `using Microsoft.JSInterop;` at top of file.

### Key Facts
- `ICookieService.GetAsync()` returns null when cookie doesn't exist -- always null-check before `.Value`
- Auth state (JWT claim) can be "authenticated" while session cookies (BaseApiUrl, UserSessionInfo) are already cleared
- `JSDisconnectedException` is thrown when circuit is disposed and any JS interop is attempted -- all logout JS calls must be wrapped
- The NullRef is the root cause; JSDisconnectedException is cascade fallout from circuit crash
- Both errors originate from concurrent OnAfterRenderAsync calls (MainLayout + MainContent) racing on the same dead session

## CHUNK 4: Qdrant Hybrid Search Full Audit and Bottleneck Fix

### Context
rag-gateway-mini on VM B1 uses Qdrant knowledge_v2 collection with hybrid search (dense nomic-embed-text + sparse djb2 BM25). Full audit and fix session covering data quality, MCP server, n8n ingest workflow, and C# QueryNormalizer.

### Problem
Multiple bottlenecks reducing retrieval quality: 168/211 chunks had MISSING chunk_type, 32 had broken string-array tags, MCP NOT_FOUND_THRESHOLD too high (0.65), query expansion hurting specific entity search, n8n workflow using wrong chunk_type field priority, QueryNormalizer padding all short queries.

### Solution
1. Auto-classified 168 MISSING chunk_type via Python scroll+rule-based classifier on VM B1. Final: debug:167, feature:23, runbook:10, checkpoint:7, decision:3, pattern:1.
2. Fixed 32 broken string-array tags via Qdrant payload update using points:[id] filter (not key filter).
3. Standardized non-standard chunk_type values: refactor->feature, ops-documentation->runbook, setup->runbook, architecture->decision.
4. MCP qdrant-mcp-server.js: NOT_FOUND_THRESHOLD 0.65->0.50, added hasProperNoun check to skip query expansion for uppercase/hyphen/underscore queries, prefetch limit limit*4->limit*6.
5. n8n ingest workflow Prepare Qdrant Point node: chunk_type now uses payload.chunk_type first with session_type fallback (was reversed), ALLOWED_STATUS expanded to include in_progress and stable.
6. C# QueryNormalizer.cs: added HasSpecificIdentity() - skips generic padding for queries with uppercase, hyphens, underscores, or dots. Lowercase generic queries still get padded to 8 words.
7. Deleted empty collections: checkpoints, architecture.
8. Installed RTK bash shim at ~/bin/rtk on VM B1.

### Key Facts
- Qdrant payload update by specific point ID requires "points":[id] parameter, NOT filter by key "id" (id is not a payload field)
- hasProperNoun check: /[A-Z]/.test(query) || /[-_]/.test(query) - uppercase OR hyphen/underscore signals specific entity
- QueryNormalizer.HasSpecificIdentity: query.Any(char.IsUpper) || Contains('-') || Contains('_') || Contains('.')
- Docker build cached src/ layer - QueryNormalizer fix verified by testing uppercase "Token Monitor" -> no padding
- NOT_FOUND_THRESHOLD 0.50 allows scores like 0.54 (RRF scale) to pass - old 0.65 cut valid results
- RTK is Windows PE32+ binary - cannot install on Linux VM B1; use lightweight bash shim at ~/bin/rtk

---

## SESSION METADATA

- **Total chunks**: 3
- **Qdrant collection**: knowledge_v2
- **Generated by**: rag_capture.py v2 -- Incremental Capture
- **Author**: Figur Ulul Azmi
- **Date**: 2026-04-20
- **Unresolved items**: (fill manually if needed)