using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Options;
using PetroChina.Eproc.RagGateway.Application.DTOs;
using PetroChina.Eproc.RagGateway.Application.Interfaces;
using PetroChina.Eproc.RagGateway.Infrastructure.Configuration;

namespace PetroChina.Eproc.RagGateway.Infrastructure.AI;

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
        string? project = null,
        CancellationToken cancellationToken = default)
        => ExecuteSearchAsync(vector, project, applyFilter: true, cancellationToken);

    public Task<List<RagResultItem>> SearchRawAsync(
        float[] vector,
        string? project = null,
        CancellationToken cancellationToken = default)
        => ExecuteSearchAsync(vector, project, applyFilter: false, cancellationToken);

    private async Task<List<RagResultItem>> ExecuteSearchAsync(
        float[] vector,
        string? project,
        bool applyFilter,
        CancellationToken cancellationToken)
    {
        object requestBody;

        if (applyFilter && !string.IsNullOrWhiteSpace(project))
        {
            requestBody = new
            {
                vector,
                limit = _options.ResultLimit,
                with_payload = true,
                filter = new
                {
                    must = new[]
                    {
                        new { key = "project", match = new { value = project } }
                    }
                }
            };
        }
        else
        {
            requestBody = new
            {
                vector,
                limit = _options.ResultLimit,
                with_payload = true
            };
        }

        var response = await _http.PostAsJsonAsync(
            $"/collections/{_options.QdrantCollection}/points/search",
            requestBody,
            cancellationToken);

        response.EnsureSuccessStatusCode();

        var qdrantResponse = await response.Content.ReadFromJsonAsync<QdrantSearchResponse>(cancellationToken)
            ?? throw new InvalidOperationException("Qdrant returned an empty search response.");

        return qdrantResponse.Result
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

    private sealed class QdrantSearchResponse
    {
        [JsonPropertyName("result")]
        public List<QdrantPoint> Result { get; set; } = [];
    }

    private sealed class QdrantPoint
    {
        [JsonPropertyName("score")]
        public float Score { get; set; }

        [JsonPropertyName("payload")]
        public Dictionary<string, JsonElement> Payload { get; set; } = [];
    }
}
