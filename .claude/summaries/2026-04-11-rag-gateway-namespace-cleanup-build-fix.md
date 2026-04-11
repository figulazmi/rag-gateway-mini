---
id: 2026-04-11-rag-gateway-namespace-cleanup-build-fix
date: 2026-04-11
source: claude-code-cli
project: rag-gateway
topic: RagGateway Namespace Cleanup and dotnet Build Fix
tags: [dotnet, csproj, namespace, build-error, aspnet-core, refactor, fixed]
related: [csproj-configuration, dotnet9, implicit-usings]
session_type: refactor
environment: dev
git_branch: main
status: implemented
chunk_source: code
---

## CHUNK 1: Remove Company-Specific Namespace from All Source Files

### Context

A standalone ASP.NET Core 9 project (`rag-gateway-mini`) had all namespaces and
`using` directives prefixed with `PetroChina.Eproc.RagGateway.*`. This was
a leftover from a company-specific repo and should be removed so the project
is fully generic and reusable.

### Problem

Every `.cs` file declared namespaces like `PetroChina.Eproc.RagGateway.Application.DTOs`
and `using PetroChina.Eproc.RagGateway.*`. The `.csproj` was also named
`PetroChina.Eproc.RagGateway.csproj` and the `Dockerfile` referenced it by that name
in `COPY`, `dotnet restore`, `dotnet publish`, and `ENTRYPOINT` directives.

### Solution

Replaced `PetroChina.Eproc.RagGateway` with `RagGateway` across all 14 source files
using targeted edits (not global find-replace on non-code lines).
Renamed the `.csproj` file via `mv` and updated the `Dockerfile` accordingly.

Files modified:
- `PetroChina.Eproc.RagGateway.csproj` → `RagGateway.csproj`
- `Program.cs` — 4 using statements
- `Controllers/RagController.cs` — using + namespace
- `Application/Services/RagSearchService.cs` — using + namespace
- `Application/DTOs/*.cs` (4 files) — namespace only
- `Application/Interfaces/*.cs` (3 files) — namespace + using
- `Infrastructure/Configuration/RagGatewayOptions.cs` — namespace
- `Infrastructure/AI/OllamaEmbeddingClient.cs` — using + namespace
- `Infrastructure/AI/QdrantVectorSearchClient.cs` — using + namespace
- `Infrastructure/Helpers/QueryNormalizer.cs` — namespace
- `Dockerfile` — COPY, restore, publish args, ENTRYPOINT dll name

### Key Facts

- Namespace rename in .NET does not require any tooling — direct string replacement works correctly as long as all `using` references are also updated.
- The `.csproj` filename does not need to match the root namespace in .NET SDK-style projects — it is just a file name.
- `Dockerfile` `ENTRYPOINT` must reference the output DLL name which by default matches the `.csproj` filename (e.g. `RagGateway.dll`).
- Verify rename completeness with `grep -r "PetroChina" .` — should return zero matches.

### Code / Commands

```bash
# Rename csproj
mv PetroChina.Eproc.RagGateway.csproj RagGateway.csproj

# Verify no references remain
grep -r "PetroChina" . --include="*.cs" --include="*.csproj" --include="Dockerfile"
```

---

## CHUNK 2: dotnet Build Fails - Missing TargetFramework and ImplicitUsings in csproj

### Context

After renaming the project, `dotnet run` was attempted on the `rag-gateway-mini`
ASP.NET Core 9 project. The `.csproj` only contained `<Nullable>enable</Nullable>`
in its `<PropertyGroup>` — both `TargetFramework` and `ImplicitUsings` were missing.
These were never in the original committed file.

### Problem

Two sequential build failures occurred:

**Failure 1 — NETSDK1013:**
```
error NETSDK1013: The TargetFramework value '' was not recognized.
It may be misspelled. If not, then the TargetFrameworkIdentifier
and/or TargetFrameworkVersion properties must be specified explicitly.
```

**Failure 2 — CS0246 (after fixing Failure 1):**
```
error CS0246: The type or namespace name 'List<>' could not be found
error CS0246: The type or namespace name 'Task<>' could not be found
error CS0246: The type or namespace name 'CancellationToken' could not be found
error CS0246: The type or namespace name 'Dictionary<,>' could not be found
error CS0246: The type or namespace name 'HttpClient' could not be found
```

### Solution

Added both missing properties to `<PropertyGroup>` in `RagGateway.csproj`:

1. `<TargetFramework>net9.0</TargetFramework>` — fixes NETSDK1013
2. `<ImplicitUsings>enable</ImplicitUsings>` — fixes all CS0246 errors

`ImplicitUsings` enables the SDK-generated global using file that automatically
imports `System`, `System.Collections.Generic`, `System.Threading`,
`System.Threading.Tasks`, `System.Net.Http`, and other common namespaces.
Without it, every file must explicitly import these types.

### Key Facts

- `<TargetFramework>` is mandatory in every .NET SDK-style project; the SDK cannot infer it.
- `<ImplicitUsings>enable</ImplicitUsings>` is what makes `List<>`, `Task<>`, `Dictionary<,>`, `CancellationToken`, and `HttpClient` available without explicit `using` statements.
- A .NET 9 Web project template sets both by default — if they are missing, the project was created without the standard template or they were manually deleted.
- Dockerfile image tag `dotnet/aspnet:9.0` confirms the correct target is `net9.0`.
- CS0246 errors on built-in BCL types (List, Task, Dictionary) are almost always caused by missing `ImplicitUsings`, not missing NuGet packages.

### Code / Commands

```xml
<!-- RagGateway.csproj — final correct PropertyGroup -->
<PropertyGroup>
  <TargetFramework>net9.0</TargetFramework>
  <Nullable>enable</Nullable>
  <ImplicitUsings>enable</ImplicitUsings>
</PropertyGroup>
```

### Caveats

- `ImplicitUsings` generates a `.cs` file under `obj/` at build time — do not manually add `using System.Collections.Generic` etc. to individual files if `ImplicitUsings` is enabled, as it creates duplicate-using warnings.
- If using a custom SDK or non-Web SDK (`Microsoft.NET.Sdk` instead of `Microsoft.NET.Sdk.Web`), the set of implicit usings differs slightly.

---

## SESSION METADATA

- **Total chunks**: 2
- **Qdrant collection**: knowledge
- **Primary project**: rag-gateway
- **Stack involved**: .NET 9, ASP.NET Core, Docker, MSBuild/SDK
- **Files modified**: RagGateway.csproj (renamed + fixed), Dockerfile, all 14 .cs source files
- **Git branch**: main
- **Unresolved items**: None — project builds and runs successfully after fixes
- **Author**: Figur Ulul Azmi
- **Generated by**: Claude Code CLI — RAG Knowledge Capture Skill
