using RagGateway.Application.DTOs;

namespace RagGateway.Application.Interfaces;

public interface IRagSearchService
{
    Task<RagSearchResponse> SearchAsync(RagSearchRequest request, CancellationToken cancellationToken = default);
    Task<RagDebugResponse> DebugAsync(RagSearchRequest request, CancellationToken cancellationToken = default);
    Task<RagAnswerResponse> AnswerAsync(RagAnswerRequest request, CancellationToken cancellationToken = default);
}
