using Microsoft.AspNetCore.Mvc;
using RagGateway.Application.DTOs;
using RagGateway.Application.Interfaces;
using Microsoft.AspNetCore.Http;

namespace RagGateway.Controllers;

[ApiController]
[Route("rag")]
[Produces("application/json")]
public sealed class RagController : ControllerBase
{
    private readonly IRagSearchService _service;

    public RagController(IRagSearchService service)
    {
        _service = service;
    }

    /// <summary>
    /// Search the RAG knowledge base. Returns retrieved knowledge or NOT FOUND.
    /// Does NOT generate or interpret answers — deterministic retrieval only.
    /// </summary>
    [HttpPost("search")]
    [ProducesResponseType(typeof(RagSearchResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Search(
        [FromBody] RagSearchRequest request,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.Query))
            return BadRequest(new { error = "Query is required." });

        var result = await _service.SearchAsync(request, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// Debug endpoint: returns ALL raw Qdrant results before threshold filtering.
    /// Use to diagnose score values and confirm connectivity.
    /// </summary>
    [HttpPost("debug")]
    [ProducesResponseType(typeof(RagDebugResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Debug(
        [FromBody] RagSearchRequest request,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.Query))
            return BadRequest(new { error = "Query is required." });

        var result = await _service.DebugAsync(request, cancellationToken);
        return Ok(result);
    }
}
