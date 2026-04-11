FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 5200

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY ["RagGateway.csproj", "."]
COPY ["Directory.Packages.props", "."]
RUN dotnet restore "RagGateway.csproj"
COPY . .
RUN dotnet publish "RagGateway.csproj" -c Release -o /app/publish --no-restore

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "RagGateway.dll"]
