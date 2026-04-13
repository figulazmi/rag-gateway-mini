using RagGateway.Application.DTOs;

namespace RagGateway.Application.Interfaces;

public interface IVectorSearchClient
{
    Task<List<RagResultItem>> SearchAsync(
        float[] vector,
        string queryText,
        string? project = null,
        string? chunkType = null,
        CancellationToken cancellationToken = default);

    Task<List<RagResultItem>> SearchRawAsync(
        float[] vector,
        string queryText,
        string? project = null,
        string? chunkType = null,
        CancellationToken cancellationToken = default);
}
