using PetroChina.Eproc.RagGateway.Application.DTOs;

namespace PetroChina.Eproc.RagGateway.Application.Interfaces;

public interface IRagSearchService
{
    Task<RagSearchResponse> SearchAsync(RagSearchRequest request, CancellationToken cancellationToken = default);
    Task<RagDebugResponse> DebugAsync(RagSearchRequest request, CancellationToken cancellationToken = default);
}
