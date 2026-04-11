using RagGateway.Application.DTOs;

namespace RagGateway.Application.Interfaces;

public interface IVectorSearchClient
{
    Task<List<RagResultItem>> SearchAsync(float[] vector, string? project = null, CancellationToken cancellationToken = default);
    Task<List<RagResultItem>> SearchRawAsync(float[] vector, string? project = null, CancellationToken cancellationToken = default);
}
