FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 5200

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY ["src/RagGateway.csproj", "src/"]
COPY ["Directory.Packages.props", "."]
RUN dotnet restore "src/RagGateway.csproj"
COPY src/ src/
RUN dotnet publish "src/RagGateway.csproj" -c Release -o /app/publish --no-restore

FROM base AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "RagGateway.dll"]
