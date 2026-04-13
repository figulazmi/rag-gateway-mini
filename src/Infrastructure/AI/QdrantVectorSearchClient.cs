using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Options;
using RagGateway.Application.DTOs;
using RagGateway.Application.Interfaces;
using RagGateway.Infrastructure.Configuration;

namespace RagGateway.Infrastructure.AI;

public sealed class QdrantVectorSearchClient : IVectorSearchClient
{
    private readonly HttpClient _http;
    private readonly RagGatewayOptions _options;

    public QdrantVectorSearchClient(HttpClient http, IOptions<RagGatewayOptions> options)
    {
        _http = http;
        _options = options.Value;

        if (!string.IsNullOrWhiteSpace(_options.QdrantApiKey))
            _http.DefaultRequestHeaders.Add("api-key", _options.QdrantApiKey);
    }

    public Task<List<RagResultItem>> SearchAsync(
        float[] vector,
        string queryText,
        string? project = null,
        string? chunkType = null,
        CancellationToken cancellationToken = default)
        => ExecuteQueryAsync(vector, queryText, project, chunkType, applyFilter: true, cancellationToken);

    public Task<List<RagResultItem>> SearchRawAsync(
        float[] vector,
        string queryText,
        string? project = null,
        string? chunkType = null,
        CancellationToken cancellationToken = default)
        => ExecuteQueryAsync(vector, queryText, project, chunkType, applyFilter: false, cancellationToken);

    private async Task<List<RagResultItem>> ExecuteQueryAsync(
        float[] vector,
        string queryText,
        string? project,
        string? chunkType,
        bool applyFilter,
        CancellationToken cancellationToken)
    {
        var prefetch = new List<object>
        {
            new
            {
                query = vector,
                @using = _options.DenseVectorName,
                limit = _options.HybridPrefetchLimit
            }
        };

        if (_options.EnableHybridSearch && !string.IsNullOrWhiteSpace(queryText))
        {
            var sparse = BuildSparseVector(queryText);
            if (sparse.Indices.Length > 0)
            {
                prefetch.Add(new
                {
                    query = new { indices = sparse.Indices, values = sparse.Values },
                    @using = _options.SparseVectorName,
                    limit = _options.HybridPrefetchLimit
                });
            }
        }

        var requestBody = new Dictionary<string, object>
        {
            ["prefetch"] = prefetch,
            ["query"] = new { fusion = _options.FusionMethod },
            ["limit"] = _options.ResultLimit,
            ["with_payload"] = true
        };

        if (applyFilter)
        {
            var must = new List<object>();
            if (!string.IsNullOrWhiteSpace(project))
                must.Add(new { key = "project", match = new { value = project } });
            if (!string.IsNullOrWhiteSpace(chunkType))
                must.Add(new { key = "chunk_type", match = new { value = chunkType } });

            if (must.Count > 0)
                requestBody["filter"] = new { must };
        }

        var response = await _http.PostAsJsonAsync(
            $"/collections/{_options.QdrantCollection}/points/query",
            requestBody,
            cancellationToken);

        response.EnsureSuccessStatusCode();

        var qdrantResponse = await response.Content.ReadFromJsonAsync<QdrantQueryResponse>(cancellationToken)
            ?? throw new InvalidOperationException("Qdrant returned an empty query response.");

        return qdrantResponse.Result.Points
            .Select(MapToRagResultItem)
            .ToList();
    }

    private static RagResultItem MapToRagResultItem(QdrantPoint point)
    {
        return new RagResultItem
        {
            Score = point.Score,
            Content = ExtractString(point.Payload, "content"),
            Metadata = point.Payload
                .Where(kv => kv.Key != "content")
                .ToDictionary(kv => kv.Key, kv => ConvertJsonElement(kv.Value))
        };
    }

    private static string ExtractString(Dictionary<string, JsonElement> payload, string key)
    {
        if (!payload.TryGetValue(key, out var element))
            return string.Empty;

        return element.ValueKind == JsonValueKind.String
            ? element.GetString() ?? string.Empty
            : element.ToString();
    }

    private static object ConvertJsonElement(JsonElement element) => element.ValueKind switch
    {
        JsonValueKind.String => element.GetString() ?? string.Empty,
        JsonValueKind.True => true,
        JsonValueKind.False => false,
        JsonValueKind.Number => element.TryGetInt64(out var l) ? (object)l : element.GetDouble(),
        JsonValueKind.Array => element.EnumerateArray().Select(ConvertJsonElement).ToArray(),
        _ => element.ToString()
    };

    /// <summary>
    /// Tokenizes <paramref name="text"/> and builds a sparse BM25 vector using djb2 hash.
    /// Must produce the same indices as the n8n ingestion pipeline's djb2 implementation.
    /// Algorithm: lowercase → split alphanum tokens → count TF → index = djb2(token) & 0x7FFFFFFF.
    /// </summary>
    private static SparseVectorPayload BuildSparseVector(string text)
    {
        var tokens = System.Text.RegularExpressions.Regex
            .Matches(text.ToLowerInvariant(), @"[a-z0-9]+")
            .Select(m => m.Value);

        var tf = new Dictionary<string, int>();
        foreach (var t in tokens)
            tf[t] = tf.TryGetValue(t, out var c) ? c + 1 : 1;

        var indices = new int[tf.Count];
        var values  = new float[tf.Count];
        int i = 0;
        foreach (var (term, freq) in tf)
        {
            int h = 5381;
            foreach (var ch in term)
                h = (((h << 5) + h) + ch) & 0x7FFFFFFF;
            indices[i] = h;
            values[i]  = freq;
            i++;
        }
        return new SparseVectorPayload(indices, values);
    }

    private readonly record struct SparseVectorPayload(int[] Indices, float[] Values);

    private sealed class QdrantQueryResponse
    {
        [JsonPropertyName("result")]
        public QdrantQueryResult Result { get; set; } = new();
    }

    private sealed class QdrantQueryResult
    {
        [JsonPropertyName("points")]
        public List<QdrantPoint> Points { get; set; } = [];
    }

    private sealed class QdrantPoint
    {
        [JsonPropertyName("score")]
        public float Score { get; set; }

        [JsonPropertyName("payload")]
        public Dictionary<string, JsonElement> Payload { get; set; } = [];
    }
}
