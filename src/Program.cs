using Microsoft.Extensions.Options;
using RagGateway.Application.Interfaces;
using RagGateway.Application.Services;
using RagGateway.Infrastructure.AI;
using RagGateway.Infrastructure.Configuration;
using Scalar.AspNetCore;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// Serilog
builder.Host.UseSerilog((ctx, cfg) => cfg.ReadFrom.Configuration(ctx.Configuration));

// Options
builder.Services.Configure<RagGatewayOptions>(
    builder.Configuration.GetSection(RagGatewayOptions.Section));

// Application
builder.Services.AddScoped<IRagSearchService, RagSearchService>();

// Infrastructure — Ollama
builder.Services.AddHttpClient<IEmbeddingClient, OllamaEmbeddingClient>((sp, client) =>
{
    var opts = sp.GetRequiredService<IOptions<RagGatewayOptions>>().Value;
    client.BaseAddress = new Uri(opts.OllamaBaseUrl);
    client.Timeout = TimeSpan.FromSeconds(30);
});

builder.Services.AddHttpClient<ILlmGenerationClient, OllamaGenerationClient>((sp, client) =>
{
    var opts = sp.GetRequiredService<IOptions<RagGatewayOptions>>().Value;
    client.BaseAddress = new Uri(opts.OllamaBaseUrl);
    client.Timeout = TimeSpan.FromMinutes(3);
});

// Infrastructure — Qdrant
builder.Services.AddHttpClient<IVectorSearchClient, QdrantVectorSearchClient>((sp, client) =>
{
    var opts = sp.GetRequiredService<IOptions<RagGatewayOptions>>().Value;
    client.BaseAddress = new Uri(opts.QdrantBaseUrl);
    client.Timeout = TimeSpan.FromSeconds(10);
});

builder.Services.AddControllers();
builder.Services.AddOpenApi();

var app = builder.Build();

app.UseHttpsRedirection();
app.MapOpenApi();
app.MapScalarApiReference();
app.MapControllers();

app.Run();
