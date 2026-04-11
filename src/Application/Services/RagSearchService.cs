using Microsoft.Extensions.Options;
using RagGateway.Application.DTOs;
using RagGateway.Application.Interfaces;
using RagGateway.Infrastructure.Configuration;
using RagGateway.Infrastructure.Helpers;
using Microsoft.Extensions.Logging;

namespace RagGateway.Application.Services;

public sealed class RagSearchService : IRagSearchService
{
    private readonly IEmbeddingClient _embedding;
    private readonly IVectorSearchClient _vector;
    private readonly ILogger<RagSearchService> _logger;
    private readonly float _threshold;

    public RagSearchService(
        IEmbeddingClient embedding,
        IVectorSearchClient vector,
        ILogger<RagSearchService> logger,
        IOptions<RagGatewayOptions> options)
    {
        _embedding = embedding;
        _vector = vector;
        _logger = logger;
        _threshold = options.Value.ScoreThreshold;
    }

    public async Task<RagSearchResponse> SearchAsync(RagSearchRequest request, CancellationToken cancellationToken = default)
    {
        var normalized = QueryNormalizer.Normalize(request.Query);

        _logger.LogInformation(
            "RAG SEARCH | original={Query} | normalized={Normalized} | project={Project}",
            request.Query, normalized, request.Project ?? "all");

        var embedding = await _embedding.GenerateEmbeddingAsync(normalized, cancellationToken);
        var results = await _vector.SearchAsync(embedding, request.Project, cancellationToken);

        var filtered = results
            .Where(r => r.Score >= _threshold)
            .OrderByDescending(r => r.Score)
            .ToList();

        _logger.LogInformation(
            "RAG RESULT | total={Total} | above_threshold={AboveThreshold} | threshold={Threshold}",
            results.Count, filtered.Count, _threshold);

        if (filtered.Count == 0)
        {
            return new RagSearchResponse
            {
                Status = "not_found",
                Message = "NOT FOUND IN RAG"
            };
        }

        return new RagSearchResponse
        {
            Status = "found",
            Query = request.Query,
            NormalizedQuery = normalized,
            Results = filtered
        };
    }

    public async Task<RagDebugResponse> DebugAsync(RagSearchRequest request, CancellationToken cancellationToken = default)
    {
        var normalized = QueryNormalizer.Normalize(request.Query);

        _logger.LogInformation(
            "RAG DEBUG | original={Query} | normalized={Normalized} | project={Project}",
            request.Query, normalized, request.Project ?? "all");

        var embedding = await _embedding.GenerateEmbeddingAsync(normalized, cancellationToken);
        var results = await _vector.SearchRawAsync(embedding, request.Project, cancellationToken);

        var aboveThreshold = results.Count(r => r.Score >= _threshold);

        _logger.LogInformation(
            "RAG DEBUG RESULT | total={Total} | above_threshold={Above} | threshold={Threshold}",
            results.Count, aboveThreshold, _threshold);

        return new RagDebugResponse
        {
            NormalizedQuery = normalized,
            ProjectFilter = request.Project,
            Threshold = _threshold,
            TotalRawResults = results.Count,
            ResultsAboveThreshold = aboveThreshold,
            Results = results.OrderByDescending(r => r.Score).ToList()
        };
    }
}
