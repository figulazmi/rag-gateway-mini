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
    private readonly RagGatewayOptions _options;

    public RagSearchService(
        IEmbeddingClient embedding,
        IVectorSearchClient vector,
        ILogger<RagSearchService> logger,
        IOptions<RagGatewayOptions> options)
    {
        _embedding = embedding;
        _vector = vector;
        _logger = logger;
        _options = options.Value;
    }

    public async Task<RagSearchResponse> SearchAsync(RagSearchRequest request, CancellationToken cancellationToken = default)
    {
        var normalized = QueryNormalizer.Normalize(request.Query);

        _logger.LogInformation(
            "RAG SEARCH | original={Query} | normalized={Normalized} | project={Project} | chunk_type={ChunkType} | feature_slug={FeatureSlug} | knowledge_expansion={KnowledgeExpansion}",
            request.Query, normalized, request.Project ?? "all", request.ChunkType ?? "all", request.FeatureSlug ?? "all", request.KnowledgeExpansion);

        if (request.KnowledgeExpansion)
            return await SearchWithExpansionAsync(normalized, request, cancellationToken);

        return await SearchSingleAsync(normalized, request, cancellationToken);
    }

    public async Task<RagDebugResponse> DebugAsync(RagSearchRequest request, CancellationToken cancellationToken = default)
    {
        var normalized = QueryNormalizer.Normalize(request.Query);

        _logger.LogInformation(
            "RAG DEBUG | original={Query} | normalized={Normalized} | project={Project} | chunk_type={ChunkType} | feature_slug={FeatureSlug} | knowledge_expansion={KnowledgeExpansion}",
            request.Query, normalized, request.Project ?? "all", request.ChunkType ?? "all", request.FeatureSlug ?? "all", request.KnowledgeExpansion);

        var queryEmbedContent = BuildEmbedContent(normalized, request.Project);
        var embedding = await _embedding.GenerateEmbeddingAsync(queryEmbedContent, cancellationToken);
        var results = await _vector.SearchRawAsync(embedding, normalized, request.Project, request.ChunkType, request.FeatureSlug, cancellationToken);

        var threshold = _options.ScoreThreshold;
        var notFoundThreshold = _options.NotFoundScoreThreshold;
        var topScore = results.OrderByDescending(r => r.Score).FirstOrDefault()?.Score ?? 0f;
        var aboveThreshold = results.Count(r => r.Score >= threshold);

        _logger.LogInformation(
            "RAG DEBUG RESULT | total={Total} | above_threshold={Above} | threshold={Threshold} | not_found_threshold={NotFoundThreshold} | top_score={TopScore}",
            results.Count, aboveThreshold, threshold, notFoundThreshold, topScore);

        var hybrid = _options.EnableHybridSearch;
        var variants = request.KnowledgeExpansion ? BuildExpansionVariants(normalized) : null;

        return new RagDebugResponse
        {
            NormalizedQuery = normalized,
            ProjectFilter = request.Project,
            ChunkTypeFilter = request.ChunkType,
            FeatureSlugFilter = request.FeatureSlug,
            KnowledgeExpansion = request.KnowledgeExpansion,
            ExpandedQueries = variants,
            SearchMode = hybrid ? "hybrid" : "dense",
            FusionMethod = hybrid ? _options.FusionMethod : null,
            PrefetchLimit = _options.HybridPrefetchLimit,
            Threshold = threshold,
            NotFoundThreshold = notFoundThreshold,
            TopScore = topScore,
            TotalRawResults = results.Count,
            ResultsAboveThreshold = aboveThreshold,
            Results = results.OrderByDescending(r => r.Score).ToList()
        };
    }

    private async Task<RagSearchResponse> SearchSingleAsync(string normalized, RagSearchRequest request, CancellationToken cancellationToken)
    {
        var queryEmbedContent = BuildEmbedContent(normalized, request.Project);
        var embedding = await _embedding.GenerateEmbeddingAsync(queryEmbedContent, cancellationToken);
        var results = await _vector.SearchAsync(embedding, normalized, request.Project, request.ChunkType, request.FeatureSlug, cancellationToken);

        return BuildResponse(request.Query, normalized, results);
    }

    private async Task<RagSearchResponse> SearchWithExpansionAsync(string normalized, RagSearchRequest request, CancellationToken cancellationToken)
    {
        var variants = BuildExpansionVariants(normalized);

        _logger.LogInformation(
            "RAG EXPANSION | variants={V0} | {V1} | {V2}",
            variants[0], variants[1], variants[2]);

        var tasks = variants.Select(async variant =>
        {
            var embedContent = BuildEmbedContent(variant, request.Project);
            var vec = await _embedding.GenerateEmbeddingAsync(embedContent, cancellationToken);
            return await _vector.SearchAsync(vec, variant, request.Project, request.ChunkType, request.FeatureSlug, cancellationToken);
        });

        var allResults = await Task.WhenAll(tasks);

        var threshold = _options.ScoreThreshold;
        var aggregated = AggregateExpansionResults(allResults, threshold);

        _logger.LogInformation(
            "RAG EXPANSION RESULT | candidates={Candidates} | variants={Variants}",
            aggregated.Count, allResults.Length);

        return BuildResponse(request.Query, normalized, aggregated);
    }

    // Returns [original, "Explain: {q}", "Describe the approach for: {q}"]
    private static List<string> BuildExpansionVariants(string normalized)
        => [normalized, $"Explain: {normalized}", $"Describe the approach for: {normalized}"];

    private static string BuildEmbedContent(string text, string? project)
        => project is { Length: > 0 } p
            ? $"This chunk is from project {p}. Content: {text}"
            : text;

    private RagSearchResponse BuildResponse(string originalQuery, string normalized, List<RagResultItem> candidates)
    {
        var threshold = _options.ScoreThreshold;
        var notFoundThreshold = _options.NotFoundScoreThreshold;

        var filtered = candidates
            .Where(r => r.Score >= threshold)
            .ToList();
        var topScore = filtered.FirstOrDefault()?.Score ?? 0f;

        _logger.LogInformation(
            "RAG RESULT | total={Total} | above_threshold={AboveThreshold} | threshold={Threshold} | not_found_threshold={NotFoundThreshold} | top_score={TopScore}",
            candidates.Count, filtered.Count, threshold, notFoundThreshold, topScore);

        if (filtered.Count == 0 || topScore < notFoundThreshold)
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
            Query = originalQuery,
            NormalizedQuery = normalized,
            Results = filtered
        };
    }

    // Union results from multiple phrasings; keep only items above threshold.
    // Rank by (hit_count DESC, best_score DESC); return top ResultLimit items.
    private List<RagResultItem> AggregateExpansionResults(List<RagResultItem>[] batches, float scoreThreshold)
    {
        var candidates = new Dictionary<string, (RagResultItem Item, int HitCount, float BestScore)>();

        foreach (var batch in batches)
        {
            foreach (var item in batch.Where(r => r.Score >= scoreThreshold))
            {
                var key = item.Metadata.TryGetValue("doc_id", out var id)
                    ? id?.ToString() ?? item.Content.GetHashCode().ToString()
                    : item.Content.GetHashCode().ToString();

                if (candidates.TryGetValue(key, out var existing))
                {
                    candidates[key] = (existing.Item, existing.HitCount + 1, Math.Max(existing.BestScore, item.Score));
                }
                else
                {
                    candidates[key] = (item, 1, item.Score);
                }
            }
        }

        return candidates.Values
            .OrderByDescending(c => c.HitCount)
            .ThenByDescending(c => c.BestScore)
            .Take(_options.ResultLimit)
            .Select(c => new RagResultItem
            {
                Score = c.BestScore,
                Content = c.Item.Content,
                Metadata = c.Item.Metadata
            })
            .ToList();
    }
}
